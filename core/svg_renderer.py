"""SVG Renderer — SlideGeometry (пиксели) → SVG-код.

Чистый Python. Контент обрезается clipPath. Таблицы адаптивные.
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
    return escape(str(t)) if t else ""


def _rx(s: str) -> int:
    return 12 if s == "soft" else 0


def _wrap(text: str, mc: int) -> list[str]:
    if not text:
        return []
    out = []
    for p in text.split("\n"):
        p = p.strip()
        if not p:
            out.append("")
            continue
        words = p.split()
        cur = ""
        for w in words:
            t = f"{cur} {w}".strip()
            if len(t) <= mc:
                cur = t
            else:
                if cur:
                    out.append(cur)
                cur = w
        if cur:
            out.append(cur)
    return out


def _mc(w: float, fpt: float = 12) -> int:
    return max(8, int(w / (fpt * 0.58 * 1.33)))


def _clip(b: BlockGeometry, svg: str) -> str:
    c = _cid()
    return (
        f'<defs><clipPath id="{c}">'
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}"/>'
        f'</clipPath></defs>\n'
        f'<g clip-path="url(#{c})">\n{svg}\n</g>'
    )


# ════════════════════════════════════════════════════════════
#  РЕНДЕРЕРЫ
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
    return "\n".join(p)


def _r_text(b: BlockGeometry, acc: str, st: str) -> str:
    c = b.content or {}
    bullets = c.get("bullet_points", [])
    body = c.get("body", "")
    title = c.get("title", "")
    mc = _mc(b.w - 16)
    lh = F_BODY * 1.7

    p = []
    y = b.y + 4

    if title:
        y += F_BTITLE * 1.33
        p.append(
            f'<text x="{b.x}" y="{y:.1f}" font-family="{FONT}" '
            f'font-size="{F_BTITLE}pt" font-weight="600" fill="{C_TEXT}">'
            f'{_e(title)}</text>'
        )
        y += 8

    y_limit = b.y + b.h - 4

    if bullets:
        for bullet in bullets:
            lines = _wrap(bullet, mc - 3)  # -3 для "•  "
            for i, line in enumerate(lines):
                y += lh
                if y > y_limit:
                    break
                prefix = "•  " if i == 0 else "   "
                p.append(
                    f'<text x="{b.x + (0 if i == 0 else 16)}" y="{y:.1f}" '
                    f'font-family="{FONT}" font-size="{F_BODY}pt" '
                    f'fill="{C_TEXT}">{_e(prefix + line)}</text>'
                )
            if y > y_limit:
                break
            y += 4  # gap между буллетами
    else:
        for line in _wrap(body, mc):
            y += lh
            if y > y_limit:
                break
            p.append(
                f'<text x="{b.x}" y="{y:.1f}" font-family="{FONT}" '
                f'font-size="{F_BODY}pt" fill="{C_TEXT}">{_e(line)}</text>'
            )

    return _clip(b, "\n".join(p))


def _r_cards(b: BlockGeometry, acc: str, st: str) -> str:
    cards = b.content.get("cards", [])
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
        title = _e(card.get("title", ""))
        body = _e(card.get("body", ""))

        p.append(
            f'<rect x="{b.x}" y="{y:.1f}" width="{b.w}" height="{ch:.1f}" '
            f'rx="{rx}" fill="{C_CARD}"/>'
        )
        ix = b.x + PAD
        iy = y + PAD
        iw = b.w - PAD * 2
        y_bot = y + ch - 8

        if num:
            p.append(
                f'<text x="{ix}" y="{iy + F_NUM:.1f}" font-family="{FONT}" '
                f'font-size="{F_NUM}pt" font-weight="700" fill="{acc}">'
                f'{_e(str(num))}</text>'
            )
            iy += F_NUM * 1.2 + 4
        elif icon:
            r = 14
            cx, cy = ix + r, iy + r
            p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{acc}" opacity="0.15"/>')
            p.append(
                f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="12pt" font-weight="600" fill="{acc}">{_e(icon[:1].upper())}</text>'
            )
            iy += r * 2 + 8

        if title:
            p.append(
                f'<text x="{ix}" y="{iy + F_BTITLE:.1f}" font-family="{FONT}" '
                f'font-size="{F_BTITLE}pt" font-weight="600" fill="{C_TEXT}">{title}</text>'
            )
            iy += F_BTITLE * 1.5

        if body:
            mc = _mc(iw, F_BODY)
            lh = F_BODY * 1.8
            ty = iy + F_BODY * 1.33
            for line in _wrap(body, mc):
                if ty > y_bot:
                    break
                p.append(
                    f'<text x="{ix}" y="{ty:.1f}" font-family="{FONT}" '
                    f'font-size="{F_BODY}pt" fill="{C_AUX}">{_e(line)}</text>'
                )
                ty += lh

        y += ch + gap

    return _clip(b, "\n".join(p))


def _r_table(b: BlockGeometry, acc: str, st: str) -> str:
    c = b.content or {}
    headers = c.get("headers", [])
    rows = c.get("rows", [])
    rx = _rx(st)

    if not headers and not rows:
        return ""

    n_cols = len(headers) if headers else (len(rows[0]) if rows else 1)

    # ── Адаптивная ширина столбцов по длине контента ──
    col_max_len = [0] * n_cols

    # Длина заголовков
    for j, h in enumerate(headers):
        col_max_len[j] = max(col_max_len[j], len(str(h).replace("\n", " ")))

    # Длина данных (смотрим все строки)
    for row in rows:
        for j, cell in enumerate(row):
            if j < n_cols:
                col_max_len[j] = max(col_max_len[j], len(str(cell)))

    # Пропорциональные веса
    total_weight = sum(max(1, l) for l in col_max_len)
    col_w = [(max(1, l) / total_weight) * b.w for l in col_max_len]

    # Минимальная ширина столбца = 50px
    for j in range(n_cols):
        if col_w[j] < 50:
            col_w[j] = 50

    # Нормализуем обратно к b.w
    sw = sum(col_w)
    if sw > 0:
        col_w = [w / sw * b.w for w in col_w]

    hdr_h = 34
    row_h = min(30, (b.h - (hdr_h if headers else 0)) / max(1, len(rows)))
    row_h = max(22, row_h)
    max_rows = int((b.h - (hdr_h if headers else 0)) / row_h)

    p = []
    total_h = min(b.h, (hdr_h if headers else 0) + min(len(rows), max_rows) * row_h)
    p.append(
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{total_h:.1f}" '
        f'rx="{rx}" fill="none" stroke="{C_BORDER}" stroke-width="0.75"/>'
    )

    y = b.y

    if headers:
        p.append(
            f'<rect x="{b.x}" y="{y}" width="{b.w}" height="{hdr_h}" '
            f'rx="{rx}" fill="{acc}" opacity="0.1"/>'
        )
        cx = b.x
        for j, h in enumerate(headers):
            w = col_w[j]
            mc = _mc(w - 12, F_AUX)
            txt = str(h).replace("\n", " ")
            if len(txt) > mc:
                txt = txt[:mc - 1] + "…"
            p.append(
                f'<text x="{cx + 6}" y="{y + hdr_h / 2 + 4:.1f}" font-family="{FONT}" '
                f'font-size="{F_AUX}pt" font-weight="600" fill="{C_TEXT}">{_e(txt)}</text>'
            )
            # Вертикальный разделитель
            if j < n_cols - 1:
                lx = cx + w
                p.append(
                    f'<line x1="{lx:.1f}" y1="{y}" x2="{lx:.1f}" y2="{y + total_h:.1f}" '
                    f'stroke="{C_BORDER}" stroke-width="0.5"/>'
                )
            cx += w
        y += hdr_h

    for i, row in enumerate(rows):
        if i >= max_rows:
            break
        if i % 2 == 1:
            p.append(
                f'<rect x="{b.x}" y="{y}" width="{b.w}" height="{row_h:.1f}" fill="#FAFAFA"/>'
            )
        cx = b.x
        for j, cell in enumerate(row):
            if j >= n_cols:
                break
            w = col_w[j]
            mc = _mc(w - 12, F_BODY)
            txt = str(cell)
            if len(txt) > mc:
                txt = txt[:mc - 1] + "…"
            p.append(
                f'<text x="{cx + 6}" y="{y + row_h / 2 + 4:.1f}" font-family="{FONT}" '
                f'font-size="{F_BODY}pt" fill="{C_TEXT}">{_e(txt)}</text>'
            )
            cx += w
        # Горизонтальная линия
        p.append(
            f'<line x1="{b.x}" y1="{y + row_h:.1f}" x2="{b.x + b.w}" y2="{y + row_h:.1f}" '
            f'stroke="{C_BORDER}" stroke-width="0.3"/>'
        )
        y += row_h

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
        mc = _mc(b.w - 40, F_AUX)
        d = str(desc)
        if len(d) > mc:
            d = d[:mc - 1] + "…"
        p.append(
            f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="{F_AUX}pt" fill="{C_AUX}">{_e(d)}</text>'
        )
    p.append(
        f'<!-- PLACEHOLDER type="{b.object_type}" subtype="{sub}" '
        f'x="{b.x}" y="{b.y}" w="{b.w}" h="{b.h}" -->'
    )
    return "\n".join(p)


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

    logger.info(f"SVG Renderer: слайд {geometry.slide_index} → {len(code)} символов, {ms}мс")
    return DesignedSlide(slide_index=geometry.slide_index, svg_code=code, generation_time_ms=ms)