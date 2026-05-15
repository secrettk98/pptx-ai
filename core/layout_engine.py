"""LayoutEngine v5.1 — детерминированная раскладка без stretchable.

Превращает LayoutPlanV5 (GridRow/GridBlock от Spatial Architect) в SlideGeometry
с пиксельными координатами и готовыми строками текста для SVG Renderer.

Принципы:
    - Размер блока известен заранее: col_span × CELL_WIDTH, height_cells × CELL_HEIGHT
    - Внутри блока — простая арифметика: курсор по Y, wrap текста по фиксированной
      ширине inner_w = block_w - 2*CARD_PADDING_PX
    - Никаких flex/measure callbacks — wrap делается один раз через text_metrics.wrap()
    - Координаты, переданные в RenderedText, синхронны с теми, что использовались
      для wrap → svg_renderer рендерит ровно то, что было измерено

Контракт: compute_geometry(plan, strategy) → SlideGeometry.
"""

from __future__ import annotations

import logging
from typing import Callable

from core.config import (
    SLIDE_MARGIN_X,
    SLIDE_MARGIN_Y,
    CELL_WIDTH,
    CELL_HEIGHT,
    GRID_ROWS,
    CARD_PADDING_PX,
    MIN_COL_WIDTH_PX,
    BULLET_TEXT_OFFSET_PX,
)
from models.contracts import (
    LayoutPlanV5,
    GridBlock,
    SlideGeometry,
    BlockGeometry,
    RenderedText,
    PresentationStrategy,
)
from core.utils.text_metrics import measure, wrap, fit_height, line_height

logger = logging.getLogger(__name__)


# ── Типографика (pt) ─────────────────────────────────────────
PT_HEAD = 24
PT_SUB = 12
PT_BTITLE = 15
PT_BODY = 12
PT_CARD_NUM = 28
PT_CARD_TITLE = 14
PT_CARD_BODY = 11
PT_TBL_HEAD = 11
PT_TBL_BODY = 10

# ── Внутренние отступы и gap'ы (px) ──────────────────────────
PAD_CARD = 18                  # внутренний padding одной карточки
PAD_TBL_X = 8                  # горизонтальный padding ячейки таблицы
PAD_TBL_Y = 6                  # вертикальный padding ячейки таблицы
GAP_INTRA_BLOCK = 8            # gap между элементами внутри текстового блока
GAP_CARDS = 12                 # gap между карточками
GAP_HEADING_ELEMENTS = 6       # gap между title/subtitle/accent_line
ACCENT_LINE_W = 60             # длина акцентной линии heading
ACCENT_LINE_H = 3              # толщина акцентной линии


# ════════════════════════════════════════════════════════════
#  АВТО-ЦЕНТРИРОВАНИЕ
# ════════════════════════════════════════════════════════════

def _compute_auto_shift_cells(plan: LayoutPlanV5) -> int:
    """Если контент прижат к верху и есть запас — центрируем по вертикали."""
    if not plan.rows:
        return 0
    min_start = min(r.row_start_cell for r in plan.rows)
    if min_start > 0:
        return 0
    max_bottom = max(r.row_start_cell + r.height_cells for r in plan.rows)
    if max_bottom >= GRID_ROWS:
        return 0
    return (GRID_ROWS - max_bottom) // 2


# ════════════════════════════════════════════════════════════
#  ФАБРИКА RenderedText
# ════════════════════════════════════════════════════════════

def _make_rendered_text(
    role: str,
    text: str,
    x: float,
    y: float,
    w: float,
    size_pt: float,
    bold: bool = False,
    extra: dict | None = None,
) -> RenderedText:
    """Делает wrap текста и упаковывает в RenderedText с реальной высотой."""
    lines = wrap(text, w, size_pt=size_pt, bold=bold) if text else []
    h = fit_height(lines, size_pt=size_pt) if lines else 0.0
    return RenderedText(
        role=role,
        lines=lines,
        size_pt=size_pt,
        bold=bold,
        x=round(x, 1),
        y=round(y, 1),
        w=round(w, 1),
        h=round(h, 1),
        extra=extra or {},
    )


# ════════════════════════════════════════════════════════════
#  БЛОК: heading
# ════════════════════════════════════════════════════════════

def _layout_heading(
    block: GridBlock, x: float, y: float, w: float, h: float
) -> list[RenderedText]:
    """heading: title (24pt bold) + опц. subtitle (12pt) + акцентная линия."""
    c = block.content or {}
    title = (c.get("title") or "").strip()
    subtitle = (c.get("subtitle") or "").strip()

    inner_x = x + CARD_PADDING_PX
    inner_y = y + CARD_PADDING_PX
    inner_w = w - 2 * CARD_PADDING_PX

    out: list[RenderedText] = []
    cur_y = inner_y

    if title:
        rt = _make_rendered_text(
            "title", title, inner_x, cur_y, inner_w, PT_HEAD, bold=True
        )
        out.append(rt)
        cur_y += rt.h + GAP_HEADING_ELEMENTS

    if subtitle:
        rt = _make_rendered_text(
            "subtitle", subtitle, inner_x, cur_y, inner_w, PT_SUB, bold=False
        )
        out.append(rt)
        cur_y += rt.h + GAP_HEADING_ELEMENTS

    # Акцентная линия — не текст, но проходит через RenderedText с w/h
    out.append(RenderedText(
        role="accent_line",
        lines=[],
        size_pt=0,
        bold=False,
        x=round(inner_x, 1),
        y=round(cur_y, 1),
        w=float(ACCENT_LINE_W),
        h=float(ACCENT_LINE_H),
        extra={},
    ))

    return out


# ════════════════════════════════════════════════════════════
#  БЛОК: text
# ════════════════════════════════════════════════════════════

def _layout_text(
    block: GridBlock, x: float, y: float, w: float, h: float
) -> list[RenderedText]:
    """text: опц. title (15pt bold) + bullets (12pt) или body (12pt)."""
    c = block.content or {}
    title = (c.get("title") or "").strip()
    body = (c.get("body") or "").strip()
    bullets = c.get("bullet_points") or []

    inner_x = x + CARD_PADDING_PX
    inner_y = y + CARD_PADDING_PX
    inner_w = w - 2 * CARD_PADDING_PX

    out: list[RenderedText] = []
    cur_y = inner_y

    if title:
        rt = _make_rendered_text(
            "title", title, inner_x, cur_y, inner_w, PT_BTITLE, bold=True
        )
        out.append(rt)
        cur_y += rt.h + GAP_INTRA_BLOCK

    if bullets:
        bullet_w = inner_w - BULLET_TEXT_OFFSET_PX
        for i, b in enumerate(bullets):
            b = str(b).strip()
            if not b:
                continue
            rt = _make_rendered_text(
                "bullet", b, inner_x, cur_y, bullet_w, PT_BODY, bold=False,
                extra={"bullet_index": i},
            )
            out.append(rt)
            cur_y += rt.h + GAP_INTRA_BLOCK
    elif body:
        rt = _make_rendered_text(
            "body", body, inner_x, cur_y, inner_w, PT_BODY, bold=False
        )
        out.append(rt)

    return out


# ════════════════════════════════════════════════════════════
#  БЛОК: card
# ════════════════════════════════════════════════════════════

def _layout_card_inner(
    card: dict, card_index: int,
    cx: float, cy: float, cw: float, ch: float,
) -> list[RenderedText]:
    """Содержимое одной карточки: number/icon → title → body."""
    inner_x = cx + PAD_CARD
    inner_y = cy + PAD_CARD
    inner_w = cw - 2 * PAD_CARD

    out: list[RenderedText] = []
    cur_y = inner_y

    num = card.get("number")
    if isinstance(num, str):
        num = num.strip()
    title = (card.get("title") or "").strip()
    body = (card.get("body") or "").strip()
    icon = card.get("icon")

    # Фон карточки прокидываем через extra первого же элемента
    common_extra: dict = {
        "card_index": card_index,
        "card_x": round(cx, 1),
        "card_y": round(cy, 1),
        "card_w": round(cw, 1),
        "card_h": round(ch, 1),
    }

    if num:
        rt = _make_rendered_text(
            "card_number", str(num), inner_x, cur_y, inner_w,
            PT_CARD_NUM, bold=True, extra=dict(common_extra),
        )
        out.append(rt)
        cur_y += rt.h + GAP_INTRA_BLOCK
    elif icon:
        # Иконка — квадрат 32×32, рендерится как кружок в svg_renderer
        out.append(RenderedText(
            role="card_icon",
            lines=[],
            size_pt=PT_CARD_TITLE,
            bold=True,
            x=round(inner_x, 1),
            y=round(cur_y, 1),
            w=32.0,
            h=32.0,
            extra={**common_extra, "icon_char": str(icon)[:1].upper()},
        ))
        cur_y += 32 + GAP_INTRA_BLOCK

    if title:
        rt = _make_rendered_text(
            "card_title", title, inner_x, cur_y, inner_w,
            PT_CARD_TITLE, bold=True, extra=dict(common_extra),
        )
        out.append(rt)
        cur_y += rt.h + GAP_INTRA_BLOCK

    if body:
        rt = _make_rendered_text(
            "card_body", body, inner_x, cur_y, inner_w,
            PT_CARD_BODY, bold=False, extra=dict(common_extra),
        )
        out.append(rt)

    return out


def _layout_card(
    block: GridBlock, x: float, y: float, w: float, h: float
) -> list[RenderedText]:
    """card: одна или несколько карточек в строку, равные доли по ширине."""
    c = block.content or {}
    cards = c.get("cards") or []

    if not cards:
        return []

    n = len(cards)
    inner_x = x + CARD_PADDING_PX
    inner_y = y + CARD_PADDING_PX
    inner_w = w - 2 * CARD_PADDING_PX
    inner_h = h - 2 * CARD_PADDING_PX

    total_gap = (n - 1) * GAP_CARDS
    card_w = max(1.0, (inner_w - total_gap) / n)
    card_h = inner_h

    out: list[RenderedText] = []
    for i, card in enumerate(cards):
        cx = inner_x + i * (card_w + GAP_CARDS)
        cy = inner_y
        out.extend(_layout_card_inner(card, i, cx, cy, card_w, card_h))

    return out


# ════════════════════════════════════════════════════════════
#  БЛОК: table — алгоритм ширин колонок (вариант A)
# ════════════════════════════════════════════════════════════

def _longest_word_width(text: str, size_pt: float, bold: bool) -> float:
    """Ширина самого длинного слова в строке — минимум, до которого можно сжать."""
    if not text:
        return 0.0
    return max(
        (measure(word, size_pt, bold) for word in str(text).split()),
        default=0.0,
    )


def _compute_col_widths(
    headers: list[str],
    rows: list[list[str]],
    inner_w: float,
    n_cols: int,
) -> list[float]:
    """Распределяет inner_w между n_cols колонками.

    Алгоритм:
        1. natural[j] = max(header_w, max_cell_w) + 2*PAD_TBL_X
        2. min[j] = max(longest_word_w, MIN_COL_WIDTH_PX) + 2*PAD_TBL_X
        3. Если sum(natural) <= inner_w → раздать остаток пропорционально natural
        4. Если sum(natural) > inner_w → сжать пропорционально, но не ниже min
        5. Если sum(min) > inner_w → physical overflow, вернуть min (warning)
    """
    natural: list[float] = []
    min_w: list[float] = []

    for j in range(n_cols):
        header_text = headers[j] if j < len(headers) else ""
        col_cells = [row[j] if j < len(row) else "" for row in rows]

        hw = measure(header_text, PT_TBL_HEAD, bold=True)
        mcw = max(
            (measure(str(c), PT_TBL_BODY, bold=False) for c in col_cells),
            default=0.0,
        )
        nat = max(hw, mcw) + 2 * PAD_TBL_X

        lw_header = _longest_word_width(header_text, PT_TBL_HEAD, bold=True)
        lw_body = max(
            (_longest_word_width(str(c), PT_TBL_BODY, bold=False) for c in col_cells),
            default=0.0,
        )
        lw = max(lw_header, lw_body, float(MIN_COL_WIDTH_PX)) + 2 * PAD_TBL_X

        natural.append(nat)
        min_w.append(lw)

    total_natural = sum(natural)
    total_min = sum(min_w)

    # Случай 1: всё помещается → пропорциональное расширение
    if total_natural <= inner_w:
        if total_natural <= 0:
            return [inner_w / n_cols] * n_cols
        extra = inner_w - total_natural
        result = [n + extra * (n / total_natural) for n in natural]
    # Случай 2: physical overflow → используем min, логируем warning
    elif total_min > inner_w:
        logger.warning(
            f"Таблица: physical overflow (sum(min)={total_min:.0f} > "
            f"inner_w={inner_w:.0f}), колонки будут урезаны до min"
        )
        result = list(min_w)
    # Случай 3: сжимаем пропорционально до min
    else:
        shrinkable = total_natural - total_min
        need = total_natural - inner_w
        result = [
            natural[j] - (natural[j] - min_w[j]) * (need / shrinkable)
            for j in range(n_cols)
        ]

    # Корректировка последней колонки на float-остаток
    diff = inner_w - sum(result)
    result[-1] += diff
    return result


def _layout_table(
    block: GridBlock, x: float, y: float, w: float, h: float
) -> list[RenderedText]:
    """table: header + rows. Ширины колонок — детерминированный алгоритм."""
    c = block.content or {}
    headers = list(c.get("headers") or [])
    rows = [list(r) for r in (c.get("rows") or [])]

    if not headers and not rows:
        return []

    n_cols = max(len(headers), max((len(r) for r in rows), default=0), 1)
    # Нормализация: добиваем пустыми ячейками
    headers = headers + [""] * (n_cols - len(headers))
    rows = [r + [""] * (n_cols - len(r)) for r in rows]

    inner_x = x  # таблица занимает всю ширину блока, без CARD_PADDING_PX
    inner_y = y
    inner_w = w
    col_widths = _compute_col_widths(headers, rows, inner_w, n_cols)

    # Накопленные X для каждой колонки
    cell_x: list[float] = [inner_x]
    for j in range(n_cols - 1):
        cell_x.append(cell_x[-1] + col_widths[j])

    out: list[RenderedText] = []
    cur_y = inner_y

    def _emit_row(cells: list[str], is_header: bool, row_idx: int) -> float:
        """Раскладывает одну строку, возвращает её высоту."""
        size_pt = PT_TBL_HEAD if is_header else PT_TBL_BODY
        bold = is_header

        # Сначала wrap каждой ячейки → собираем строки и высоты
        per_cell: list[tuple[list[str], float]] = []
        for j in range(n_cols):
            text_w = col_widths[j] - 2 * PAD_TBL_X
            lines = wrap(str(cells[j]), text_w, size_pt=size_pt, bold=bold)
            text_h = fit_height(lines, size_pt=size_pt)
            per_cell.append((lines, text_h))

        row_h = max((th for _, th in per_cell), default=0.0) + 2 * PAD_TBL_Y

        for j in range(n_cols):
            lines, text_h = per_cell[j]
            cw = col_widths[j]
            cx = cell_x[j]
            # Вертикальное центрирование внутри ячейки
            text_y = cur_y + PAD_TBL_Y + max(0.0, (row_h - 2 * PAD_TBL_Y - text_h) / 2)
            text_x = cx + PAD_TBL_X
            text_w = cw - 2 * PAD_TBL_X

            extra = {
                "row": row_idx,
                "col": j,
                "is_header": is_header,
                "cell_x": round(cx, 1),
                "cell_y": round(cur_y, 1),
                "cell_w": round(cw, 1),
                "cell_h": round(row_h, 1),
            }
            out.append(RenderedText(
                role="cell_header" if is_header else "cell_body",
                lines=lines,
                size_pt=size_pt,
                bold=bold,
                x=round(text_x, 1),
                y=round(text_y, 1),
                w=round(text_w, 1),
                h=round(text_h, 1),
                extra=extra,
            ))

        return row_h

    # Header (row_idx = -1)
    if any(headers):
        row_h = _emit_row(headers, is_header=True, row_idx=-1)
        cur_y += row_h

    # Data rows
    for i, r in enumerate(rows):
        row_h = _emit_row(r, is_header=False, row_idx=i)
        cur_y += row_h

    if cur_y > y + h:
        logger.warning(
            f"Таблица {block.block_id}: вертикальный overflow "
            f"({cur_y - (y + h):.0f}px). Будет видна часть до границы блока."
        )

    return out


# ════════════════════════════════════════════════════════════
#  БЛОК: placeholder (chart / visual)
# ════════════════════════════════════════════════════════════

def _layout_placeholder(
    block: GridBlock, x: float, y: float, w: float, h: float
) -> list[RenderedText]:
    """chart/visual — пустой список, svg_renderer сам рисует заглушку."""
    return []


# ── Реестр layout'еров ────────────────────────────────────────

_LAYOUTERS: dict[str, Callable] = {
    "heading": _layout_heading,
    "text": _layout_text,
    "card": _layout_card,
    "table": _layout_table,
    "chart": _layout_placeholder,
    "visual": _layout_placeholder,
}


def _layout_block(
    block: GridBlock, x: float, y: float, w: float, h: float
) -> list[RenderedText]:
    """Диспетчер по semantic_type."""
    fn = _LAYOUTERS.get(block.semantic_type, _layout_placeholder)
    return fn(block, x, y, w, h)


# ════════════════════════════════════════════════════════════
#  ПУБЛИЧНЫЙ API
# ════════════════════════════════════════════════════════════

def compute_geometry(
    layout_plan: LayoutPlanV5,
    strategy: PresentationStrategy,
) -> SlideGeometry:
    """LayoutPlanV5 (клетки 12×27) → SlideGeometry (пиксели).

    Алгоритм:
        1. Auto-shift для вертикального центрирования
        2. Каждый блок: x=col_start*CELL_WIDTH, y=row_start_cell*CELL_HEIGHT
           (+ margins, + auto_shift)
        3. Размер блока: col_span × CELL_WIDTH, height_cells × CELL_HEIGHT
        4. Внутреннее содержимое раскладывает _layout_block — детерминированно
    """
    auto_shift = _compute_auto_shift_cells(layout_plan)
    if auto_shift > 0:
        logger.info(
            f"Слайд {layout_plan.slide_index}: авто-центрирование "
            f"со сдвигом {auto_shift} клеток вниз"
        )

    blocks_out: list[BlockGeometry] = []

    for row in layout_plan.rows:
        row_y_px = SLIDE_MARGIN_Y + (row.row_start_cell + auto_shift) * CELL_HEIGHT

        for block in row.blocks:
            block_x_px = SLIDE_MARGIN_X + block.col_start * CELL_WIDTH
            block_w_px = block.col_span * CELL_WIDTH
            block_h_px = block.height_cells * CELL_HEIGHT

            try:
                rendered = _layout_block(
                    block, block_x_px, row_y_px, block_w_px, block_h_px
                )
            except Exception as e:
                logger.error(
                    f"Ошибка layout блока {block.block_id} "
                    f"({block.semantic_type}): {e}"
                )
                raise

            blocks_out.append(BlockGeometry(
                block_id=block.block_id,
                x=round(block_x_px, 1),
                y=round(row_y_px, 1),
                w=round(block_w_px, 1),
                h=round(block_h_px, 1),
                object_type=block.semantic_type,
                content=block.content,
                render=block.render,
                visual_subtype=block.visual_subtype,
                rendered_texts=rendered,
            ))

    footer_out = layout_plan.footer if layout_plan.needs_footer else None

    result = SlideGeometry(
        slide_index=layout_plan.slide_index,
        slide_role=layout_plan.slide_role,
        header_type=layout_plan.header_type,
        style_mode=layout_plan.style_mode,
        accent_color=strategy.accent_color,
        blocks=blocks_out,
        footer=footer_out,
    )

    logger.info(
        f"LayoutEngine v5.1: слайд {layout_plan.slide_index} → "
        f"{len(blocks_out)} блоков, auto_shift={auto_shift}"
    )
    return result