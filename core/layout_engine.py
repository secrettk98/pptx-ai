"""LayoutEngine v5 — клеточная сетка 12×27 → точные пиксели.

Превращает LayoutPlanV5 (GridRow/GridBlock от Spatial Architect)
в SlideGeometry с пиксельными координатами и готовыми строками для SVG Renderer.

Архитектура:
    - Ряды позиционируются absolute по row_start_cell × CELL_HEIGHT
    - Внутри ряда блоки получают фиксированную ширину col_span × CELL_WIDTH
    - stretchable используется только для внутренней структуры блоков
      (wrap текста, карточки, ячейки таблиц)
    - Авто-центрирование: если Architect прижал контент к верху и есть запас,
      все ряды сдвигаются на (GRID_ROWS - total_used) // 2 клеток вниз

Контракт: compute_geometry(plan, strategy) → SlideGeometry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from math import isnan
from typing import Optional

from stretchable import Node, Edge
from stretchable.style import AUTO
from stretchable.style.geometry.length import Scale
from stretchable.style.geometry.size import SizePoints
from stretchable.style.props import FlexDirection, AlignItems

from core.config import (
    SLIDE_WIDTH,
    SLIDE_HEIGHT,
    SLIDE_MARGIN_X,
    SLIDE_MARGIN_Y,
    WORKING_AREA_W,
    WORKING_AREA_H,
    CELL_WIDTH,
    CELL_HEIGHT,
    GRID_COLS,
    GRID_ROWS,
    ROW_GAP_CELLS,
)
from models.contracts import (
    LayoutPlanV5,
    GridRow,
    GridBlock,
    SlideGeometry,
    BlockGeometry,
    RenderedText,
    PresentationStrategy,
)
from core.utils.text_metrics import measure_block, line_height

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

# ── Внутренние отступы блоков (px) ────────────────────────────
PAD_CARD = 18
PAD_TBL_X = 8
PAD_TBL_Y = 6
GAP_INTRA_BLOCK = 8        # вертикальный gap внутри блока между текстами
GAP_CARDS = 12             # gap между карточками
GAP_TABLE_ROW = 0          # gap между рядами таблицы (управляется padding)
GAP_TABLE_COL = 0          # gap между колонками таблицы


# ════════════════════════════════════════════════════════════
#  КОНТЕЙНЕР: связь Node ↔ метаданные блока
# ════════════════════════════════════════════════════════════

@dataclass
class BlockCtx:
    """Контекст блока — связь stretchable Node и данных GridBlock."""
    node: Node
    block: GridBlock
    text_specs: list[dict] = field(default_factory=list)
    wrapper_nodes: list[dict] = field(default_factory=list)
    # Абсолютные координаты ряда — выставляются на этапе сборки
    row_x: float = 0.0
    row_y: float = 0.0
    block_w: float = 0.0
    block_h: float = 0.0


# ════════════════════════════════════════════════════════════
#  ИЗМЕРИТЕЛЬ ТЕКСТА (measure_func для stretchable)
# ════════════════════════════════════════════════════════════

def _make_text_measure(text: str, size_pt: float, bold: bool = False):
    """Фабрика measure-функции для текстового листового узла.

    Возвращает width=available (не actual!) — это критично для wrap.
    Если вернуть actual_w, Node займёт только нужную ширину, но при
    повторном wrap-е в _collect_rendered_texts эта ширина окажется
    меньше фактической и текст обрежется.
    """
    def measure(node, known_dimensions, available_space):
        kw = known_dimensions.width.value
        aw = available_space.width
        if not isnan(kw):
            w = float(kw)
        elif aw.scale == Scale.POINTS and not isnan(aw.value):
            w = float(aw.value)
        else:
            w = 10000.0
        _, actual_h, _ = measure_block(text, w, size_pt=size_pt, bold=bold)
        # Возвращаем width=w (доступную), а не actual_w — wrap должен
        # происходить именно по этой ширине и в layout_engine, и в svg_renderer
        return SizePoints(width=w, height=actual_h)
    return measure


# ════════════════════════════════════════════════════════════
#  СТРОИТЕЛИ ВНУТРЕННЕЙ СТРУКТУРЫ БЛОКОВ
#  Каждый builder создаёт корневой Node с фиксированными размерами слота
#  (col_span × CELL_WIDTH, height_cells × CELL_HEIGHT) и наполняет внутренним
#  контентом для wrap текста / распределения карточек / ячеек таблиц.
# ════════════════════════════════════════════════════════════

def _slot_node(block: GridBlock, gap: int = GAP_INTRA_BLOCK) -> Node:
    """Корневой Node блока с фиксированным размером в пикселях."""
    w = block.col_span * CELL_WIDTH
    h = block.height_cells * CELL_HEIGHT
    return Node(
        size=(w, h),
        flex_direction=FlexDirection.COLUMN,
        gap=gap,
        align_items=AlignItems.STRETCH,
    )


def _build_heading(block: GridBlock) -> BlockCtx:
    """heading: title (24pt bold) + опц. subtitle (12pt) + акцентная линия."""
    c = block.content or {}
    title = (c.get("title") or "").strip()
    subtitle = (c.get("subtitle") or "").strip()

    container = _slot_node(block, gap=6)

    text_specs: list[dict] = []

    if title:
        n = Node(measure=_make_text_measure(title, PT_HEAD, bold=True))
        container.add(n)
        text_specs.append({
            "role": "title", "text": title,
            "size_pt": PT_HEAD, "bold": True, "_node": n,
        })

    if subtitle:
        n = Node(measure=_make_text_measure(subtitle, PT_SUB))
        container.add(n)
        text_specs.append({
            "role": "subtitle", "text": subtitle,
            "size_pt": PT_SUB, "bold": False, "_node": n,
        })

    line_node = Node(size=(60, 3))
    container.add(line_node)
    text_specs.append({
        "role": "accent_line", "text": "",
        "size_pt": 0, "bold": False, "_node": line_node,
    })

    return BlockCtx(node=container, block=block, text_specs=text_specs)


def _build_text(block: GridBlock) -> BlockCtx:
    """text: опц. title (15pt bold) + body или bullets (12pt)."""
    c = block.content or {}
    title = (c.get("title") or "").strip()
    body = (c.get("body") or "").strip()
    bullets = c.get("bullet_points") or []

    container = _slot_node(block)
    text_specs: list[dict] = []

    if title:
        n = Node(measure=_make_text_measure(title, PT_BTITLE, bold=True))
        container.add(n)
        text_specs.append({
            "role": "title", "text": title,
            "size_pt": PT_BTITLE, "bold": True, "_node": n,
        })

    if bullets:
        for i, b in enumerate(bullets):
            b = str(b).strip()
            if not b:
                continue
            n = Node(measure=_make_text_measure(b, PT_BODY))
            container.add(n)
            text_specs.append({
                "role": "bullet", "text": b,
                "size_pt": PT_BODY, "bold": False, "_node": n,
                "extra": {"bullet_index": i},
            })
    elif body:
        n = Node(measure=_make_text_measure(body, PT_BODY))
        container.add(n)
        text_specs.append({
            "role": "body", "text": body,
            "size_pt": PT_BODY, "bold": False, "_node": n,
        })

    return BlockCtx(node=container, block=block, text_specs=text_specs)


def _build_placeholder(block: GridBlock) -> BlockCtx:
    """chart/visual — пустой слот заданного размера (рендер через external)."""
    return BlockCtx(node=_slot_node(block), block=block, text_specs=[])


def _build_card_inner(card: dict, card_index: int) -> tuple[Node, list[dict]]:
    """Одна карточка — flex column с числом/иконкой + title + body."""
    container = Node(
        flex_direction=FlexDirection.COLUMN,
        gap=6,
        padding=PAD_CARD,
        flex_grow=1.0,
        flex_shrink=1.0,
        flex_basis=0,
        align_items=AlignItems.STRETCH,
    )
    specs: list[dict] = []

    num = card.get("number")
    if isinstance(num, str):
        num = num.strip()
    title = (card.get("title") or "").strip()
    body = (card.get("body") or "").strip()
    icon = card.get("icon")

    if num:
        n = Node(measure=_make_text_measure(str(num), PT_CARD_NUM, bold=True))
        container.add(n)
        specs.append({
            "role": "card_number", "text": str(num),
            "size_pt": PT_CARD_NUM, "bold": True, "_node": n,
            "extra": {"card_index": card_index},
        })
    elif icon:
        n = Node(size=(32, 32))
        container.add(n)
        specs.append({
            "role": "card_icon", "text": str(icon),
            "size_pt": PT_CARD_TITLE, "bold": True, "_node": n,
            "extra": {"card_index": card_index, "icon_char": str(icon)[:1].upper()},
        })

    if title:
        n = Node(measure=_make_text_measure(title, PT_CARD_TITLE, bold=True))
        container.add(n)
        specs.append({
            "role": "card_title", "text": title,
            "size_pt": PT_CARD_TITLE, "bold": True, "_node": n,
            "extra": {"card_index": card_index},
        })

    if body:
        n = Node(measure=_make_text_measure(body, PT_CARD_BODY))
        container.add(n)
        specs.append({
            "role": "card_body", "text": body,
            "size_pt": PT_CARD_BODY, "bold": False, "_node": n,
            "extra": {"card_index": card_index},
        })

    return container, specs


def _build_card(block: GridBlock) -> BlockCtx:
    """card-блок: контейнер + одна или несколько карточек внутри."""
    c = block.content or {}
    cards = c.get("cards") or []

    container = _slot_node(block, gap=GAP_CARDS)

    text_specs: list[dict] = []
    wrapper_nodes: list[dict] = []

    if not cards:
        return BlockCtx(node=container, block=block, text_specs=[])

    for i, card in enumerate(cards):
        card_node, specs = _build_card_inner(card, card_index=i)
        container.add(card_node)
        text_specs.extend(specs)
        wrapper_nodes.append({"kind": "card", "index": i, "node": card_node})

    return BlockCtx(
        node=container, block=block,
        text_specs=text_specs, wrapper_nodes=wrapper_nodes,
    )


def _build_table(block: GridBlock) -> BlockCtx:
    """Таблица: flex column из ряда заголовков + рядов данных."""
    c = block.content or {}
    headers = c.get("headers") or []
    rows = c.get("rows") or []

    n_cols = max(len(headers), max((len(r) for r in rows), default=0), 1)
    headers = list(headers) + [""] * (n_cols - len(headers))
    norm_rows: list[list[str]] = []
    for r in rows:
        rl = list(r) + [""] * (n_cols - len(r))
        norm_rows.append(rl[:n_cols])

    def col_weight(j: int) -> float:
        from core.utils.text_metrics import measure as _measure
        samples = [str(headers[j])] + [str(r[j]) for r in norm_rows[:20]]
        return max((_measure(s, PT_TBL_BODY) for s in samples), default=40.0)

    raw_weights = [col_weight(j) for j in range(n_cols)]
    sorted_w = sorted(raw_weights)
    median = sorted_w[len(sorted_w) // 2]
    cap = max(120.0, median * 3.0)
    weights = [min(cap, max(60.0, w)) for w in raw_weights]

    container = _slot_node(block, gap=GAP_TABLE_ROW)

    text_specs: list[dict] = []
    wrapper_nodes: list[dict] = []

    def build_row(
        cells: list[str], is_header: bool, row_idx: int
    ) -> tuple[Node, list[dict]]:
        size_pt = PT_TBL_HEAD if is_header else PT_TBL_BODY
        bold = is_header
        cell_nodes: list[dict] = []
        row_node = Node(
            flex_direction=FlexDirection.ROW,
            gap=GAP_TABLE_COL,
            align_items=AlignItems.STRETCH,
            size=(AUTO, AUTO),
        )
        for j, val in enumerate(cells):
            val = str(val).strip()
            cell = Node(
                flex_grow=weights[j],
                flex_shrink=1.0,
                flex_basis=0,
                padding=(PAD_TBL_Y, PAD_TBL_X, PAD_TBL_Y, PAD_TBL_X),
            )
            if val:
                tnode = Node(measure=_make_text_measure(val, size_pt, bold=bold))
                cell.add(tnode)
                text_specs.append({
                    "role": "cell_header" if is_header else "cell_body",
                    "text": val, "size_pt": size_pt, "bold": bold, "_node": tnode,
                    "extra": {"row": row_idx, "col": j, "is_header": is_header},
                })
            row_node.add(cell)
            cell_nodes.append({
                "kind": "cell", "row": row_idx, "col": j, "node": cell,
            })
        return row_node, cell_nodes

    if headers:
        rn, cn = build_row(headers, is_header=True, row_idx=-1)
        container.add(rn)
        wrapper_nodes.extend(cn)
    for i, r in enumerate(norm_rows):
        rn, cn = build_row(r, is_header=False, row_idx=i)
        container.add(rn)
        wrapper_nodes.extend(cn)

    return BlockCtx(
        node=container, block=block,
        text_specs=text_specs, wrapper_nodes=wrapper_nodes,
    )


# ── Реестр строителей ─────────────────────────────────────────

_BUILDERS: dict = {
    "heading": _build_heading,
    "text": _build_text,
    "card": _build_card,
    "table": _build_table,
    "chart": _build_placeholder,
    "visual": _build_placeholder,
}


def _build_block(block: GridBlock) -> BlockCtx:
    """Выбирает строителя по semantic_type блока."""
    builder = _BUILDERS.get(block.semantic_type, _build_placeholder)
    return builder(block)


# ════════════════════════════════════════════════════════════
#  АВТО-ЦЕНТРИРОВАНИЕ
# ════════════════════════════════════════════════════════════

def _compute_auto_shift_cells(plan: LayoutPlanV5) -> int:
    """Если контент прижат к верху и есть запас — центрируем по вертикали.

    Возвращает количество клеток, на которое нужно сдвинуть все ряды вниз.
    Если Architect уже расставил с offset'ом (min row_start_cell > 0) — 0.
    """
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
#  ВЫЧИСЛЕНИЕ АБСОЛЮТНЫХ КООРДИНАТ
# ════════════════════════════════════════════════════════════

def _abs_box_within(node: Node) -> tuple[float, float, float, float]:
    """Относительные координаты узла в пределах своего поддерева."""
    x, y = 0.0, 0.0
    cur = node
    while cur is not None and cur.parent is not None:
        b = cur.get_box(Edge.BORDER)
        x += b.x
        y += b.y
        cur = cur.parent
    b_self = node.get_box(Edge.BORDER)
    return x, y, b_self.width, b_self.height


def _collect_rendered_texts(
    ctx: BlockCtx,
    block_origin_x: float,
    block_origin_y: float,
) -> list[RenderedText]:
    """Считает абс. координаты текстов в блоке и делает финальный wrap."""
    out: list[RenderedText] = []

    for spec in ctx.text_specs:
        node: Node = spec["_node"]
        rx, ry, rw, rh = _abs_box_within(node)
        ax = block_origin_x + rx
        ay = block_origin_y + ry

        _, _, lines = measure_block(
            spec["text"], rw, size_pt=spec["size_pt"], bold=spec["bold"]
        )

        out.append(RenderedText(
            role=spec["role"],
            lines=lines,
            size_pt=spec["size_pt"],
            bold=spec["bold"],
            x=round(ax, 1),
            y=round(ay, 1),
            w=round(rw, 1),
            h=round(rh, 1),
            extra=spec.get("extra", {}),
        ))

    if ctx.wrapper_nodes:
        wrappers: dict[str, tuple[float, float, float, float]] = {}
        for wn in ctx.wrapper_nodes:
            key = (
                f"{wn['kind']}_{wn.get('index', '')}_"
                f"{wn.get('row', '')}_{wn.get('col', '')}"
            )
            rx, ry, rw, rh = _abs_box_within(wn["node"])
            wrappers[key] = (
                block_origin_x + rx, block_origin_y + ry, rw, rh
            )

        for rt in out:
            if rt.role.startswith("card_"):
                ci = rt.extra.get("card_index")
                if ci is not None:
                    key = f"card_{ci}__"
                    if key in wrappers:
                        wx, wy, ww, wh = wrappers[key]
                        rt.extra["card_x"] = round(wx, 1)
                        rt.extra["card_y"] = round(wy, 1)
                        rt.extra["card_w"] = round(ww, 1)
                        rt.extra["card_h"] = round(wh, 1)
            elif rt.role in ("cell_header", "cell_body"):
                row = rt.extra.get("row")
                col = rt.extra.get("col")
                if row is not None and col is not None:
                    key = f"cell__{row}_{col}"
                    if key in wrappers:
                        wx, wy, ww, wh = wrappers[key]
                        rt.extra["cell_x"] = round(wx, 1)
                        rt.extra["cell_y"] = round(wy, 1)
                        rt.extra["cell_w"] = round(ww, 1)
                        rt.extra["cell_h"] = round(wh, 1)
                        text_h = len(rt.lines) * line_height(rt.size_pt)
                        if wh > text_h:
                            rt.y = round(wy + (wh - text_h) / 2, 1)

    return out


# ════════════════════════════════════════════════════════════
#  ПУБЛИЧНЫЙ API
# ════════════════════════════════════════════════════════════

def compute_geometry(
    layout_plan: LayoutPlanV5,
    strategy: PresentationStrategy,
) -> SlideGeometry:
    """LayoutPlanV5 (клетки 12×27) → SlideGeometry (пиксели).

    Алгоритм:
        1. Считаем auto-shift для вертикального центрирования
        2. Для каждого ряда: позиция Y = (row_start_cell + shift) × CELL_HEIGHT
        3. Для каждого блока в ряду: позиция X = col_start × CELL_WIDTH,
           размеры (col_span × CELL_WIDTH, height_cells × CELL_HEIGHT)
        4. Строим внутреннее дерево stretchable для каждого блока отдельно
        5. compute_layout() на каждом блоке → wrap текста
        6. Собираем BlockGeometry с абсолютными координатами
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

            ctx = _build_block(block)
            ctx.row_x = block_x_px
            ctx.row_y = row_y_px
            ctx.block_w = block_w_px
            ctx.block_h = block_h_px

            try:
                ctx.node.compute_layout()
            except Exception as e:
                logger.error(
                    f"Ошибка compute_layout для блока {block.block_id}: {e}"
                )
                raise

            rendered = _collect_rendered_texts(ctx, block_x_px, row_y_px)

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
        f"LayoutEngine v5: слайд {layout_plan.slide_index} → "
        f"{len(blocks_out)} блоков, auto_shift={auto_shift}"
    )
    return result