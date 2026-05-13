"""SVG Renderer — SlideGeometry (пиксели) → SVG-код.

Чистый Python:
- точный word-wrap по пиксельной ширине;
- аккуратные буллеты;
- таблицы с переносом текста;
- clipPath защищает от вылезания контента.
"""

import logging
import time
from xml.sax.saxutils import escape

from models.contracts import SlideGeometry, BlockGeometry, FooterInstruction, DesignedSlide

logger = logging.getLogger(__name__)

SLIDE_W = 1280
SLIDE_H = 720
FONT = "Google Sans, Arial, sans-serif"

F_HEAD = 24
F_SUB = 12
F_BTITLE = 15
F_BODY = 12
F_AUX = 10
F_NUM = 28

C_BG = "#FFFFFF"
C_CARD = "#F8F8F8"
C_TEXT = "#1A1A1A"
C_AUX = "#6B7280"
C_BORDER = "#E5E7EB"

PAD = 24
FOOTER_H = 30
FOOTER_Y = SLIDE_H - 20 - FOOTER_H

_clip_n = 0


def _cid() -> str:
    global _clip_n
    _clip_n += 1
    return f"cl{_clip_n}"


def _e(t) -> str:
    return escape(str(t)) if t is not None else ""


def _rx(style_mode: str) -> int:
    return 12 if style_mode == "soft" else 0


def _clip(b: BlockGeometry, svg: str) -> str:
    c = _cid()
    return (
        f'<defs><clipPath id="{c}">'
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}"/>'
        f'</clipPath></defs>\n'
        f'<g clip-path="url(#{c})">\n{svg}\n</g>'
    )


# ════════════════════════════════════════════════════════════
#  TEXT UTILS
# ════════════════════════════════════════════════════════════

def _char_em(ch: str) -> float:
    """Примерная ширина символа."""
    if ch == " ":
        return 0.32
    if ch in ".,:;!|'`":
        return 0.25
    if ch in "-–—_/\\()[]{}":
        return 0.35
    if ch in "mwMW@#%&":
        return 0.85
    if ch.isdigit():
        return 0.55
    if "\u0400" <= ch <= "\u04FF":  # кириллица
        return 0.62 if ch.isupper() else 0.56
    if ch.isupper():
        return 0.62
    return 0.50


def _text_width(text: str, fpt: float = 12) -> float:
    """Примерная ширина текста в пикселях."""
    return sum(_char_em(ch) for ch in str(text)) * fpt * 1.33


def _split_long_word(word: str, max_w: float, fpt: float) -> list[str]:
    parts = []
    cur = ""

    for ch in str(word):
        test = cur + ch
        if _text_width(test, fpt) <= max_w or not cur:
            cur = test
        else:
            parts.append(cur)
            cur = ch

    if cur:
        parts.append(cur)

    return parts


def _wrap(text: str, max_w: float, fpt: float = 12) -> list[str]:
    """Перенос текста по пиксельной ширине."""
    if not text:
        return []

    out = []

    for paragraph in str(text).split("\n"):
        paragraph = paragraph.strip()

        if not paragraph:
            out.append("")
            continue

        cur = ""

        for word in paragraph.split():
            test = f"{cur} {word}".strip()

            if _text_width(test, fpt) <= max_w:
                cur = test
                continue

            if cur:
                out.append(cur)

            if _text_width(word, fpt) > max_w:
                parts = _split_long_word(word, max_w, fpt)
                out.extend(parts[:-1])
                cur = parts[-1] if parts else ""
            else:
                cur = word

        if cur:
            out.append(cur)

    return out


def _truncate_px(text: str, max_w: float, fpt: float = 12) -> str:
    """Обрезка текста с многоточием по ширине."""
    text = str(text)

    if _text_width(text, fpt) <= max_w:
        return text

    out = ""
    for ch in text:
        if _text_width(out + ch + "…", fpt) > max_w:
            break
        out += ch

    return out + "…"



# ════════════════════════════════════════════════════════════
#  RENDERERS
# ════════════════════════════════════════════════════════════

def _r_heading(b: BlockGeometry, acc: str, st: str) -> str:
    title = _e(b.content.get("title", ""))
    sub = _e(b.content.get("subtitle", ""))

    p = []

    ty = b.y + F_HEAD * 1.33
    p.append(
        f'<text x="{b.x}" y="{ty:.1f}" font-family="{FONT}" '
        f'font-size="{F_HEAD}pt" font-weight="700" fill="{C_TEXT}">{title}</text>'
    )

    if sub:
        sy = ty + F_HEAD * 0.6 + F_SUB * 1.33
        p.append(
            f'<text x="{b.x}" y="{sy:.1f}" font-family="{FONT}" '
            f'font-size="{F_SUB}pt" fill="{C_AUX}">{sub}</text>'
        )

    ly = b.y + b.h - 1
    p.append(
        f'<line x1="{b.x}" y1="{ly:.1f}" x2="{b.x + 60}" y2="{ly:.1f}" '
        f'stroke="{acc}" stroke-width="3" stroke-linecap="round"/>'
    )

    return _clip(b, "\n".join(p))


def _r_text(b: BlockGeometry, acc: str, st: str) -> str:
    c = b.content or {}
    bullets = c.get("bullet_points", []) or []
    body = c.get("body", "") or ""
    title = c.get("title", "") or ""

    p = []
    y = b.y + 4
    y_limit = b.y + b.h - 4
    text_w = b.w - 28

    if title:
        y += F_BTITLE * 1.25
        p.append(
            f'<text x="{b.x}" y="{y:.1f}" font-family="{FONT}" '
            f'font-size="{F_BTITLE}pt" font-weight="600" fill="{C_TEXT}">{_e(title)}</text>'
        )
        y += 8

    available_h = max(20, y_limit - y)

    if bullets:
        bullet_x = b.x
        text_x = b.x + 18
        line_w = max(40, b.w - 46)

        prepared = []
        for bullet in bullets:
            lines = _wrap(str(bullet), line_w, F_BODY)
            prepared.append(lines)

        total_lines = sum(len(x) for x in prepared)
        f_body = F_BODY
        lh = F_BODY * 1.35

        for lines in prepared:
            for i, line in enumerate(lines):
                y += lh
                if y > y_limit:
                    break

                if i == 0:
                    p.append(
                        f'<text x="{bullet_x}" y="{y:.1f}" font-family="{FONT}" '
                        f'font-size="{f_body}pt" fill="{C_TEXT}">•</text>'
                    )

                p.append(
                    f'<text x="{text_x}" y="{y:.1f}" font-family="{FONT}" '
                    f'font-size="{f_body}pt" fill="{C_TEXT}">{_e(line)}</text>'
                )

            if y > y_limit:
                break

            y += 3

    else:
        lines = _wrap(body, text_w, F_BODY)
        f_body = F_BODY
        lh = F_BODY * 1.35

        for line in lines:
            y += lh
            if y > y_limit:
                break

            p.append(
                f'<text x="{b.x}" y="{y:.1f}" font-family="{FONT}" '
                f'font-size="{f_body}pt" fill="{C_TEXT}">{_e(line)}</text>'
            )

    return _clip(b, "\n".join(p))


def _r_cards(b: BlockGeometry, acc: str, st: str) -> str:
    cards = b.content.get("cards", []) or []

    if not cards:
        return ""

    rx = _rx(st)
    p = []

    n = len(cards)
    gap = 16
    ch = (b.h - gap * max(0, n - 1)) / max(1, n)
    y = b.y

    for card in cards:
        num = card.get("number", "")
        icon = card.get("icon", "")
        title = card.get("title", "")
        body = card.get("body", "")

        p.append(
            f'<rect x="{b.x}" y="{y:.1f}" width="{b.w}" height="{ch:.1f}" '
            f'rx="{rx}" fill="{C_CARD}"/>'
        )

        ix = b.x + PAD
        iy = y + PAD
        iw = b.w - PAD * 2
        y_bot = y + ch - 10

        if num:
            p.append(
                f'<text x="{ix}" y="{iy + F_NUM:.1f}" font-family="{FONT}" '
                f'font-size="{F_NUM}pt" font-weight="700" fill="{acc}">{_e(num)}</text>'
            )
            iy += F_NUM * 1.2 + 4

        elif icon:
            r = 14
            cx, cy = ix + r, iy + r
            p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{acc}" opacity="0.15"/>')
            p.append(
                f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="12pt" font-weight="600" fill="{acc}">{_e(str(icon)[:1].upper())}</text>'
            )
            iy += r * 2 + 8

        if title:
            p.append(
                f'<text x="{ix}" y="{iy + F_BTITLE:.1f}" font-family="{FONT}" '
                f'font-size="{F_BTITLE}pt" font-weight="600" fill="{C_TEXT}">{_e(title)}</text>'
            )
            iy += F_BTITLE * 1.45

        if body:
            lines = _wrap(body, iw, F_BODY)
            available_h = max(20, y_bot - iy)
            f_body = F_BODY
            lh = F_BODY * 1.35

            ty = iy + f_body * 1.25
            for line in lines:
                if ty > y_bot:
                    break

                p.append(
                    f'<text x="{ix}" y="{ty:.1f}" font-family="{FONT}" '
                    f'font-size="{f_body}pt" fill="{C_AUX}">{_e(line)}</text>'
                )
                ty += lh

        y += ch + gap

    return _clip(b, "\n".join(p))


def _r_table(b: BlockGeometry, acc: str, st: str) -> str:
    c = b.content or {}
    headers = c.get("headers", []) or []
    rows = c.get("rows", []) or []
    rx = _rx(st)

    if not headers and not rows:
        return ""

    n_cols = max(len(headers), max((len(r) for r in rows), default=0), 1)
    headers = list(headers) + [""] * (n_cols - len(headers))

    norm_rows = []
    for row in rows:
        r = list(row) + [""] * (n_cols - len(row))
        norm_rows.append(r[:n_cols])

    def clean(v) -> str:
        return str(v).replace("\n", " ").strip()

    T_HEAD = 9.0
    T_BODY = 9.5
    HEAD_LH = T_HEAD * 1.25
    BODY_LH = T_BODY * 1.25
    PAD_X = 7
    PAD_Y = 4

    # ── ширина колонок ─────────────────────────────
    weights = []
    for j in range(n_cols):
        samples = [clean(headers[j])] + [clean(r[j]) for r in norm_rows[:12]]
        longest = max((_text_width(s, T_BODY) for s in samples), default=40)
        weights.append(min(max(longest, 40), 260))

    min_col = max(34, min(70, b.w / n_cols * 0.62))

    if min_col * n_cols >= b.w:
        col_w = [b.w / n_cols] * n_cols
    else:
        extra = b.w - min_col * n_cols
        total = sum(weights) or 1
        col_w = [min_col + extra * w / total for w in weights]

    # ── красивый перенос: делим текст на равные строки ─────────
    def wrap_balanced(value, width: float, fpt: float, max_lines: int) -> list[str]:
        text = clean(value)
        if not text:
            return [""]

        max_w = max(18, width - PAD_X * 2)
        words = text.split()

        if not words:
            return [""]

        total_w = _text_width(text, fpt)
        line_count = max(1, min(max_lines, round(total_w / max_w + 0.49)))

        if line_count <= 1:
            return [_truncate_px(text, max_w, fpt)]

        target_w = total_w / line_count
        lines = []
        cur = ""

        for word in words:
            test = f"{cur} {word}".strip()

            if not cur:
                cur = word
                continue

            cur_w = _text_width(cur, fpt)
            test_w = _text_width(test, fpt)

            # если текущая строка уже около идеальной ширины — переносим
            if cur_w >= target_w * 0.75 and len(lines) < line_count - 1:
                lines.append(cur)
                cur = word
            elif test_w <= max_w:
                cur = test
            else:
                lines.append(cur)
                cur = word

        if cur:
            lines.append(cur)

        # если получилось больше — склеиваем хвост
        while len(lines) > max_lines:
            lines[-2] = f"{lines[-2]} {lines[-1]}"
            lines.pop()

        # финальная защита по ширине
        return [_truncate_px(line, max_w, fpt) for line in lines]

    # ── высоты: таблица занимает ВЕСЬ блок ──────────
    header_h = 0
    if headers:
        header_h = max(28, min(46, b.h * 0.18))

    body_count = max(1, len(norm_rows))
    body_h = max(1, b.h - header_h)
    row_h = body_h / body_count

    header_max_lines = max(1, int((header_h - PAD_Y * 2) / HEAD_LH)) if header_h else 1
    body_max_lines = max(1, int((row_h - PAD_Y * 2) / BODY_LH))

    header_cells = [
        wrap_balanced(h, col_w[j], T_HEAD, header_max_lines)
        for j, h in enumerate(headers)
    ]

    prepared_rows = []
    for row in norm_rows:
        cells = [
            wrap_balanced(cell, col_w[j], T_BODY, body_max_lines)
            for j, cell in enumerate(row)
        ]
        prepared_rows.append(cells)

    p = []

    # внешний контур на всю высоту блока
    p.append(
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" '
        f'rx="{rx}" fill="none" stroke="{C_BORDER}" stroke-width="0.75"/>'
    )

    # header background
    y = b.y
    if headers:
        p.append(
            f'<rect x="{b.x}" y="{y:.1f}" width="{b.w}" height="{header_h:.1f}" '
            f'rx="{rx}" fill="{acc}" opacity="0.10"/>'
        )

        cx = b.x
        for j, lines in enumerate(header_cells):
            total_text_h = len(lines) * HEAD_LH
            ty = y + (header_h - total_text_h) / 2 + T_HEAD

            for line in lines:
                p.append(
                    f'<text x="{cx + PAD_X:.1f}" y="{ty:.1f}" font-family="{FONT}" '
                    f'font-size="{T_HEAD}pt" font-weight="700" fill="{C_TEXT}">{_e(line)}</text>'
                )
                ty += HEAD_LH

            cx += col_w[j]

        y += header_h

    # body rows
    for i, cells in enumerate(prepared_rows):
        if i % 2 == 1:
            p.append(
                f'<rect x="{b.x}" y="{y:.1f}" width="{b.w}" height="{row_h:.1f}" fill="#FAFAFA"/>'
            )

        cx = b.x
        for j, lines in enumerate(cells):
            total_text_h = len(lines) * BODY_LH
            ty = y + (row_h - total_text_h) / 2 + T_BODY

            for line in lines:
                p.append(
                    f'<text x="{cx + PAD_X:.1f}" y="{ty:.1f}" font-family="{FONT}" '
                    f'font-size="{T_BODY}pt" fill="{C_TEXT}">{_e(line)}</text>'
                )
                ty += BODY_LH

            cx += col_w[j]

        # горизонтальная линия
        p.append(
            f'<line x1="{b.x}" y1="{y + row_h:.1f}" x2="{b.x + b.w}" y2="{y + row_h:.1f}" '
            f'stroke="{C_BORDER}" stroke-width="0.30"/>'
        )

        y += row_h

    # vertical lines на всю высоту
    cx = b.x
    for j in range(n_cols - 1):
        cx += col_w[j]
        p.append(
            f'<line x1="{cx:.1f}" y1="{b.y}" x2="{cx:.1f}" y2="{b.y + b.h}" '
            f'stroke="{C_BORDER}" stroke-width="0.40"/>'
        )

    return _clip(b, "\n".join(p))


def _r_placeholder(b: BlockGeometry, acc: str, st: str) -> str:
    rx = _rx(st)
    sub = b.visual_subtype or b.object_type
    label = _e(f"[{sub}]")
    desc = b.content.get("description", b.content.get("chart_type", ""))

    p = []

    p.append(
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" '
        f'rx="{rx}" fill="#F9FAFB" stroke="{acc}" '
        f'stroke-width="1.5" stroke-dasharray="8 4"/>'
    )

    cx = b.x + b.w / 2
    cy = b.y + b.h / 2

    p.append(
        f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="14pt" font-weight="600" fill="{acc}">{label}</text>'
    )

    if desc:
        d = _truncate_px(str(desc), b.w - 40, F_AUX)
        p.append(
            f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="{F_AUX}pt" fill="{C_AUX}">{_e(d)}</text>'
        )

    p.append(
        f'<!-- PLACEHOLDER type="{b.object_type}" subtype="{sub}" '
        f'x="{b.x}" y="{b.y}" w="{b.w}" h="{b.h}" -->'
    )

    return _clip(b, "\n".join(p))


def _r_footer(footer: FooterInstruction, acc: str) -> str:
    p = []
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
    "heading": _r_heading,
    "text": _r_text,
    "card": _r_cards,
    "table": _r_table,
    "chart": _r_placeholder,
    "visual": _r_placeholder,
}


def render_slide(geometry: SlideGeometry) -> DesignedSlide:
    global _clip_n
    _clip_n = 0

    t0 = time.time()
    acc = geometry.accent_color
    st = geometry.style_mode

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {SLIDE_W} {SLIDE_H}" width="{SLIDE_W}" height="{SLIDE_H}">',
        f'<!-- Slide {geometry.slide_index} | {geometry.slide_role} '
        f'| header={geometry.header_type} | style={st} -->',
        f'<rect width="{SLIDE_W}" height="{SLIDE_H}" fill="{C_BG}"/>',
        "",
    ]

    for bl in geometry.blocks:
        fn = _MAP.get(bl.object_type)

        if bl.render == "external":
            fn = _r_placeholder

        if fn:
            svg.append(f"<!-- {bl.col_id}: {bl.object_type} -->")
            svg.append(fn(bl, acc, st))
            svg.append("")
        else:
            logger.warning(f"Нет рендерера: {bl.object_type}")

    if geometry.footer:
        svg.append("<!-- footer -->")
        svg.append(_r_footer(geometry.footer, acc))

    svg.append("</svg>")

    code = "\n".join(svg)
    ms = int((time.time() - t0) * 1000)

    logger.info(
        f"SVG Renderer: слайд {geometry.slide_index} → "
        f"{len(code)} символов, {ms}мс"
    )

    return DesignedSlide(
        slide_index=geometry.slide_index,
        svg_code=code,
        generation_time_ms=ms,
    )