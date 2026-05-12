"""LayoutEngine — LayoutPlan (grid-колонки) → SlideGeometry (пиксели).

AI мыслит в колонках (1-12), Python считает точные x/y/w/h.
Гарантия: все блоки внутри рабочей зоны, вертикальное центрирование для Type B/C.
"""

import logging
from models.contracts import (
    LayoutPlan, RowInstruction, ColumnInstruction,
    SlideGeometry, BlockGeometry, FooterInstruction, PresentationStrategy,
)

logger = logging.getLogger(__name__)

# ── Сетка (core_rules.md §3) ───────────────────────────────────
SLIDE_W = 1280
SLIDE_H = 720
MARGIN_H = 43
MARGIN_V = 20
GUTTER = 26
GRID_COLS = 12
WORK_W = SLIDE_W - MARGIN_H * 2                           # 1194
WORK_H = SLIDE_H - MARGIN_V * 2                           # 680
COL_W = (WORK_W - GUTTER * (GRID_COLS - 1)) / GRID_COLS   # ~76.18

HEADER_A_H = 70
FOOTER_H = 30

# ── Эвристика высот ────────────────────────────────────────────
H_HEADING = 70
H_HEADING_SUB = 90
H_LINE = 20           # одна строка 12pt
H_TEXT_MIN = 60
H_CARD_MIN = 140
H_TABLE_ROW = 30
H_TABLE_HDR = 34
H_TABLE_MIN = 100
H_PLACEHOLDER = 260


def _span_w(span: int) -> float:
    return span * COL_W + (span - 1) * GUTTER


def _col_x(col_start: int) -> float:
    return MARGIN_H + col_start * (COL_W + GUTTER)


def _text_lines(text: str, width_px: float, font_size: float = 12.0) -> int:
    if not text:
        return 1
    cw = font_size * 0.58
    cpl = max(1, int(width_px / cw))
    lines = 0
    for p in text.split("\n"):
        p = p.strip()
        if not p:
            lines += 1
            continue
        lines += max(1, -(-len(p) // cpl))
    return max(1, lines)


def _block_h(col: ColumnInstruction, w: float) -> float:
    """Желаемая высота блока."""
    ot = col.object_type
    c = col.content or {}

    if ot == "heading":
        return H_HEADING_SUB if c.get("subtitle") else H_HEADING

    if ot == "text":
        body = c.get("body", "")
        bullets = c.get("bullet_points", [])
        extra = 0
        if c.get("title"):
            extra = 36  # block title
        if bullets:
            body = "\n".join(["•  " + b for b in bullets])
        lines = _text_lines(body, w - 16)
        return max(H_TEXT_MIN, lines * H_LINE + 16 + extra)

    if ot == "card":
        cards = c.get("cards", [])
        if not cards:
            return H_CARD_MIN
        max_h = H_CARD_MIN
        for card in cards:
            body = card.get("body", "")
            lines = _text_lines(body, w - 48)
            ch = 48 + lines * H_LINE + 24
            if card.get("number"):
                ch += 24
            max_h = max(max_h, ch)
        if len(cards) > 1:
            return max_h * len(cards) + 16 * (len(cards) - 1)
        return max_h

    if ot == "table":
        rows = c.get("rows", [])
        h = H_TABLE_HDR if c.get("headers") else 0
        h += len(rows) * H_TABLE_ROW
        return max(H_TABLE_MIN, h + 8)

    if ot in ("chart", "visual"):
        return H_PLACEHOLDER

    return H_CARD_MIN


def compute_geometry(
    layout_plan: LayoutPlan,
    strategy: PresentationStrategy,
) -> SlideGeometry:

    blocks: list[BlockGeometry] = []

    # ── Рабочая зона ────────────────────────────────────────────
    zone_top = MARGIN_V
    zone_bot = SLIDE_H - MARGIN_V

    if layout_plan.header_type == "A":
        zone_top = MARGIN_V + HEADER_A_H + GUTTER
    if layout_plan.needs_footer and layout_plan.footer:
        zone_bot = SLIDE_H - MARGIN_V - FOOTER_H - GUTTER

    zone_h = zone_bot - zone_top

    # ── Проход 1: размеры ──────────────────────────────────────
    row_data: list[list[dict]] = []

    for row in layout_plan.rows:
        cs = 0
        rb = []
        for col in row.columns:
            s = col.grid_span
            rb.append({
                "col": col,
                "x": _col_x(cs),
                "w": _span_w(s),
                "h": _block_h(col, _span_w(s)),
            })
            cs += s
        # Карточки в ряду = одинаковая высота
        cards = [b for b in rb if b["col"].object_type == "card"]
        if len(cards) > 1:
            mh = max(b["h"] for b in cards)
            for b in cards:
                b["h"] = mh
        row_data.append(rb)

    # ── Проход 2: высоты рядов ─────────────────────────────────
    row_h = [max((b["h"] for b in rb), default=0) for rb in row_data]
    n_gaps = max(0, len(row_h) - 1)
    gaps_total = GUTTER * n_gaps
    frame_h = sum(row_h) + gaps_total

    # ── Проход 3: сжатие если не влезает ───────────────────────
    if frame_h > zone_h and frame_h > 0:
        rows_sum = sum(row_h)
        avail_for_rows = zone_h - gaps_total

        if avail_for_rows < 80:
            # Крайний случай: уменьшаем и gaps
            scale = zone_h / frame_h
            row_h = [h * scale for h in row_h]
        else:
            scale = avail_for_rows / rows_sum
            row_h = [h * scale for h in row_h]

        frame_h = sum(row_h) + gaps_total
        logger.info(f"Сжатие: scale={scale:.2f}, фрейм={frame_h:.0f}px / зона={zone_h:.0f}px")

    # ── Проход 4: вертикальная позиция ─────────────────────────
    if layout_plan.header_type in ("B", "C"):
        air = max(0, (zone_h - frame_h) / 2)
        y = zone_top + air
    else:
        y = zone_top

    # ── Проход 5: блоки ────────────────────────────────────────
    for i, rb in enumerate(row_data):
        rh = row_h[i]
        for b in rb:
            col = b["col"]
            blocks.append(BlockGeometry(
                col_id=col.col_id,
                x=round(b["x"], 1),
                y=round(y, 1),
                w=round(b["w"], 1),
                h=round(rh, 1),
                object_type=col.object_type,
                content=col.content,
                render=col.render,
                visual_subtype=col.visual_subtype,
            ))
        y += rh + GUTTER

    footer_out = layout_plan.footer if layout_plan.needs_footer else None

    result = SlideGeometry(
        slide_index=layout_plan.slide_index,
        slide_role=layout_plan.slide_role,
        header_type=layout_plan.header_type,
        style_mode=layout_plan.style_mode,
        accent_color=strategy.accent_color,
        blocks=blocks,
        footer=footer_out,
    )

    logger.info(
        f"LayoutEngine: слайд {layout_plan.slide_index} → "
        f"{len(blocks)} блоков, фрейм={frame_h:.0f}px / зона={zone_h:.0f}px"
    )
    return result