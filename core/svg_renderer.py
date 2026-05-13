"""SVG Renderer v5 — тупой рендерер по готовым координатам RenderedText.

Получает SlideGeometry (точные пиксели + готовые строки) от LayoutEngine v5.
НЕ делает wrap / truncate / измерений — только рисует.

Порядок отрисовки каждого блока:
    1. Фон (card → заливка, placeholder → пунктир, table → рамка)
    2. Спец-элементы (акцент-линия heading, иконка card, сетка table)
    3. Текст (проход по rendered_texts — строки как есть)
"""

from __future__ import annotations

import logging
import time
from xml.sax.saxutils import escape

from models.contracts import (
    SlideGeometry, BlockGeometry, FooterInstruction,
    RenderedText, DesignedSlide,
)
from core.text_metrics import line_height, baseline_offset as _get_baseline

logger = logging.getLogger(__name__)

# ── Константы слайда ──────────────────────────────────────────
SLIDE_W = 1280
SLIDE_H = 720
FONT = "Inter, Google Sans, Arial, sans-serif"

# ── Цвета ─────────────────────────────────────────────────────
C_BG = "#FFFFFF"
C_CARD = "#F8F8F8"
C_TEXT = "#1A1A1A"
C_AUX = "#6B7280"
C_BORDER = "#E5E7EB"
C_ZEBRA = "#FAFAFA"

# ── Футер ─────────────────────────────────────────────────────
FOOTER_H = 30
FOOTER_Y = SLIDE_H - 20 - FOOTER_H
F_AUX = 10

# ── Clip counter ──────────────────────────────────────────────
_clip_n = 0


def _cid() -> str:
    global _clip_n
    _clip_n += 1
    return f"cl{_clip_n}"


def _e(t) -> str:
    """Escape XML."""
    return escape(str(t)) if t is not None else ""


def _rx(style_mode: str) -> int:
    """Скругление углов: soft=12, strict=0."""
    return 12 if style_mode == "soft" else 0


def _clip(b: BlockGeometry, svg: str) -> str:
    """Оборачивает SVG-контент в clipPath по границам блока."""
    c = _cid()
    return (
        f'<defs><clipPath id="{c}">'
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}"/>'
        f'</clipPath></defs>\n'
        f'<g clip-path="url(#{c})">\n{svg}\n</g>'
    )


# ════════════════════════════════════════════════════════════
#  ОТРИСОВКА ТЕКСТОВ (общая для всех блоков)
# ════════════════════════════════════════════════════════════

def _color_for_role(role: str, accent: str) -> str:
    """Цвет текста по роли."""
    if role in ("subtitle", "card_body"):
        return C_AUX
    if role == "card_number":
        return accent
    return C_TEXT


def _weight_for_role(role: str) -> str:
    """font-weight по роли (bold уже в RenderedText, но для SVG нужна строка)."""
    # bold из RenderedText используется для метрик;
    # здесь дублируем для SVG-атрибута
    return "700" if role in ("title", "card_number", "card_title", "cell_header") else "400"


def _render_text_lines(rt: RenderedText, accent: str) -> list[str]:
    """Рисует строки одного RenderedText. Возвращает список SVG-элементов."""
    if not rt.lines:
        return []

    out: list[str] = []
    color = _color_for_role(rt.role, accent)
    weight = _weight_for_role(rt.role)
    lh = line_height(rt.size_pt)

    # Буллеты: рисуем точку перед первой строкой
    is_bullet = rt.role == "bullet"
    bullet_offset = 18  # отступ текста от точки

    # Вертикальное центрирование для ячеек таблицы
    start_y = rt.y  # layout engine уже отцентрировал

    # SVG baseline ≈ 75% от line_height (ascender)
    baseline_offset = lh * 0.75

    boff = _get_baseline(rt.size_pt, rt.bold)

    for i, line in enumerate(rt.lines):
        ty = start_y + i * lh + boff

        if is_bullet and i == 0:
            out.append(
                f'<text x="{rt.x:.1f}" y="{ty:.1f}" font-family="{FONT}" '
                f'font-size="{rt.size_pt}pt" fill="{color}">•</text>'
            )

        tx = rt.x + (bullet_offset if is_bullet else 0)

        out.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" font-family="{FONT}" '
            f'font-size="{rt.size_pt}pt" font-weight="{weight}" '
            f'fill="{color}">{_e(line)}</text>'
        )

    return out


# ════════════════════════════════════════════════════════════
#  БЛОКИ: heading
# ════════════════════════════════════════════════════════════

def _draw_heading(b: BlockGeometry, accent: str, style_mode: str) -> str:
    """heading: тексты + акцентная линия. Всё по координатам из RenderedText."""
    p: list[str] = []

    for rt in b.rendered_texts:
        if rt.role == "accent_line":
            # Линия рисуется по координатам узла
            ly = rt.y + rt.h / 2
            p.append(
                f'<line x1="{rt.x}" y1="{ly:.1f}" x2="{rt.x + 60}" y2="{ly:.1f}" '
                f'stroke="{accent}" stroke-width="3" stroke-linecap="round"/>'
            )
        else:
            p.extend(_render_text_lines(rt, accent))

    return _clip(b, "\n".join(p))


# ════════════════════════════════════════════════════════════
#  БЛОКИ: text
# ════════════════════════════════════════════════════════════

def _draw_text(b: BlockGeometry, accent: str, style_mode: str) -> str:
    """text: просто рисуем все rendered_texts."""
    p: list[str] = []

    for rt in b.rendered_texts:
        p.extend(_render_text_lines(rt, accent))

    return _clip(b, "\n".join(p))


# ════════════════════════════════════════════════════════════
#  БЛОКИ: card
# ════════════════════════════════════════════════════════════

def _draw_card(b: BlockGeometry, accent: str, style_mode: str) -> str:
    """card: фон каждой карточки + иконки + тексты."""
    rx = _rx(style_mode)
    p: list[str] = []

    # 1) Фоны карточек (собираем уникальные card_index)
    drawn_cards: set[int] = set()
    for rt in b.rendered_texts:
        ci = rt.extra.get("card_index")
        if ci is not None and ci not in drawn_cards:
            cx = rt.extra.get("card_x")
            cy = rt.extra.get("card_y")
            cw = rt.extra.get("card_w")
            ch = rt.extra.get("card_h")
            if cx is not None:
                p.append(
                    f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" '
                    f'rx="{rx}" fill="{C_CARD}"/>'
                )
                drawn_cards.add(ci)

    # 2) Иконки и тексты
    for rt in b.rendered_texts:
        if rt.role == "card_icon":
            # Кружок с буквой
            icon_char = rt.extra.get("icon_char", "?")
            r = 14
            cx = rt.x + r
            cy = rt.y + r
            p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{accent}" opacity="0.15"/>')
            p.append(
                f'<text x="{cx:.1f}" y="{cy + 5:.1f}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="12pt" font-weight="600" fill="{accent}">{_e(icon_char)}</text>'
            )
        else:
            p.extend(_render_text_lines(rt, accent))

    return _clip(b, "\n".join(p))


# ════════════════════════════════════════════════════════════
#  БЛОКИ: table
# ════════════════════════════════════════════════════════════

def _draw_table(b: BlockGeometry, accent: str, style_mode: str) -> str:
    """table: рамка + зебра + сетка + тексты. Всё по координатам ячеек из extra."""
    rx = _rx(style_mode)
    p: list[str] = []

    # Внешняя рамка
    p.append(
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" '
        f'rx="{rx}" fill="none" stroke="{C_BORDER}" stroke-width="0.75"/>'
    )

    # Собираем уникальные ячейки для рисования фонов и линий
    cells: dict[tuple[int, int], dict] = {}  # (row, col) → {cell_x/y/w/h, is_header}
    for rt in b.rendered_texts:
        row = rt.extra.get("row")
        col = rt.extra.get("col")
        if row is not None and col is not None and (row, col) not in cells:
            cx = rt.extra.get("cell_x")
            if cx is not None:
                cells[(row, col)] = {
                    "x": rt.extra["cell_x"],
                    "y": rt.extra["cell_y"],
                    "w": rt.extra["cell_w"],
                    "h": rt.extra["cell_h"],
                    "is_header": rt.extra.get("is_header", False),
                }

    # Уникальные ряды
    rows_info: dict[int, dict] = {}  # row_idx → {y, h, is_header}
    for (row, col), info in cells.items():
        if row not in rows_info:
            rows_info[row] = {"y": info["y"], "h": info["h"], "is_header": info["is_header"]}

    # Header фон (акцент, прозрачный)
    for row_idx, ri in rows_info.items():
        if ri["is_header"]:
            p.append(
                f'<rect x="{b.x}" y="{ri["y"]:.1f}" width="{b.w}" height="{ri["h"]:.1f}" '
                f'rx="{rx}" fill="{accent}" opacity="0.10"/>'
            )

    # Зебра (нечётные data-ряды)
    data_rows = sorted([r for r in rows_info if not rows_info[r]["is_header"]])
    for i, row_idx in enumerate(data_rows):
        if i % 2 == 1:
            ri = rows_info[row_idx]
            p.append(
                f'<rect x="{b.x}" y="{ri["y"]:.1f}" width="{b.w}" height="{ri["h"]:.1f}" '
                f'fill="{C_ZEBRA}"/>'
            )

    # Горизонтальные линии (под каждым рядом)
    for row_idx, ri in rows_info.items():
        ly = ri["y"] + ri["h"]
        p.append(
            f'<line x1="{b.x}" y1="{ly:.1f}" x2="{b.x + b.w}" y2="{ly:.1f}" '
            f'stroke="{C_BORDER}" stroke-width="0.30"/>'
        )

    # Вертикальные линии (между колонками)
    # Берём col=0..n-1 для одного ряда, рисуем правую границу каждой колонки кроме последней
    any_row = next(iter(rows_info), None)
    if any_row is not None:
        cols_in_row = sorted([(c, info) for (r, c), info in cells.items() if r == any_row], key=lambda x: x[0])
        for col_idx, info in cols_in_row[:-1]:  # все кроме последней
            vx = info["x"] + info["w"]
            p.append(
                f'<line x1="{vx:.1f}" y1="{b.y}" x2="{vx:.1f}" y2="{b.y + b.h}" '
                f'stroke="{C_BORDER}" stroke-width="0.40"/>'
            )

    # Тексты
    for rt in b.rendered_texts:
        p.extend(_render_text_lines(rt, accent))

    return _clip(b, "\n".join(p))


# ════════════════════════════════════════════════════════════
#  БЛОКИ: placeholder (chart / visual)
# ════════════════════════════════════════════════════════════

def _draw_placeholder(b: BlockGeometry, accent: str, style_mode: str) -> str:
    """placeholder: пунктирная рамка + подпись."""
    rx = _rx(style_mode)
    sub = b.visual_subtype or b.object_type
    label = _e(f"[{sub}]")
    desc = b.content.get("description", b.content.get("chart_type", ""))

    p: list[str] = []

    p.append(
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" '
        f'rx="{rx}" fill="#F9FAFB" stroke="{accent}" '
        f'stroke-width="1.5" stroke-dasharray="8 4"/>'
    )

    cx = b.x + b.w / 2
    cy = b.y + b.h / 2

    p.append(
        f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="14pt" font-weight="600" fill="{accent}">{label}</text>'
    )

    if desc:
        # Простая обрезка — если текст длинный, показываем первые ~60 символов
        d = str(desc)[:60] + ("…" if len(str(desc)) > 60 else "")
        p.append(
            f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="{F_AUX}pt" fill="{C_AUX}">{_e(d)}</text>'
        )

    p.append(
        f'<!-- PLACEHOLDER type="{b.object_type}" subtype="{sub}" '
        f'x="{b.x}" y="{b.y}" w="{b.w}" h="{b.h}" -->'
    )

    return _clip(b, "\n".join(p))


# ════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════

def _draw_footer(footer: FooterInstruction, accent: str) -> str:
    """Футер: линия + текст слева/справа."""
    p: list[str] = []
    yt = FOOTER_Y + FOOTER_H / 2 + 4

    p.append(
        f'<line x1="43" y1="{FOOTER_Y}" x2="1237" y2="{FOOTER_Y}" '
        f'stroke="{C_BORDER}" stroke-width="0.75"/>'
    )

    if footer.left:
        p.append(
            f'<text x="43" y="{yt:.1f}" font-family="{FONT}" '
            f'font-size="{F_AUX}pt" fill="{C_AUX}">{_e(footer.left)}</text>'
        )

    if footer.right:
        p.append(
            f'<text x="1237" y="{yt:.1f}" text-anchor="end" font-family="{FONT}" '
            f'font-size="{F_AUX}pt" fill="{C_AUX}">{_e(footer.right)}</text>'
        )

    return "\n".join(p)


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════

_MAP = {
    "heading": _draw_heading,
    "text": _draw_text,
    "card": _draw_card,
    "table": _draw_table,
    "chart": _draw_placeholder,
    "visual": _draw_placeholder,
}


def render_slide(geometry: SlideGeometry) -> DesignedSlide:
    """Главный вход: SlideGeometry → DesignedSlide (SVG-код)."""
    global _clip_n
    _clip_n = 0

    t0 = time.time()
    acc = geometry.accent_color
    st = geometry.style_mode

    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {SLIDE_W} {SLIDE_H}" width="{SLIDE_W}" height="{SLIDE_H}">',
        f'<!-- Slide {geometry.slide_index} | {geometry.slide_role} '
        f'| header={geometry.header_type} | style={st} | renderer=v5 -->',
        f'<rect width="{SLIDE_W}" height="{SLIDE_H}" fill="{C_BG}"/>',
        "",
    ]

    for bl in geometry.blocks:
        fn = _MAP.get(bl.object_type)

        if bl.render == "external":
            fn = _draw_placeholder

        if fn:
            svg.append(f"<!-- {bl.col_id}: {bl.object_type} -->")
            svg.append(fn(bl, acc, st))
            svg.append("")
        else:
            logger.warning(f"Нет рендерера: {bl.object_type}")

    if geometry.footer:
        svg.append("<!-- footer -->")
        svg.append(_draw_footer(geometry.footer, acc))

    svg.append("</svg>")

    code = "\n".join(svg)
    ms = int((time.time() - t0) * 1000)

    logger.info(
        f"SVG Renderer v5: слайд {geometry.slide_index} → "
        f"{len(code)} символов, {ms}мс"
    )

    return DesignedSlide(
        slide_index=geometry.slide_index,
        svg_code=code,
        generation_time_ms=ms,
    )