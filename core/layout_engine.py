"""LayoutEngine v5 — flex-движок на stretchable + точные метрики Pillow/Inter.

Превращает LayoutPlanV5 (GridRow/GridBlock от Spatial Architect)
в SlideGeometry (точные пиксели + готовые строки для SVG Renderer).

Архитектура дерева stretchable:
    SlideRoot (column, padding=margins)
     ├─ HeaderRow [optional, type A]
     ├─ ContentRoot (column, flex_grow=1)
     │   ├─ Row 0 (row, gap=gutter)
     │   │   ├─ Slot (%-ширина) → Block
     │   │   └─ Slot → Block
     │   └─ Row N
     └─ FooterRow [optional]

Контракт: compute_geometry(plan, strategy) → SlideGeometry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from math import isnan
from typing import Optional

from stretchable import Node, Edge
from stretchable.style import AUTO, PCT
from stretchable.style.geometry.length import Scale
from stretchable.style.geometry.size import SizePoints
from stretchable.style.props import FlexDirection, AlignItems, JustifyContent

from models.contracts import (
    LayoutPlanV5,
    GridRow,
    GridBlock,
    SlideGeometry,
    BlockGeometry,
    RenderedText,
    PresentationStrategy,
    FooterInstruction,
)
from core.utils.text_metrics import measure_block, line_height, baseline_offset

logger = logging.getLogger(__name__)


# ── Геометрия слайда ─────────────────────────────────────────
SLIDE_W = 1280
SLIDE_H = 720
MARGIN_H = 43
MARGIN_V = 20
GUTTER = 26

HEADER_A_H = 70
FOOTER_H = 30

# ── Типографика (pt) ─────────────────────────────────────────
PT_HEAD = 24
PT_SUB = 12
PT_BTITLE = 15
PT_BODY = 12
PT_AUX = 10

# Минимальные высоты блоков
MIN_H_HEADING = 50
MIN_H_TEXT = 50
MIN_H_PLACEHOLDER = 200
MIN_H_CARD = 140
MIN_H_TABLE = 100

# Внутренние отступы
PAD_BLOCK = 14
PAD_CARD = 18

# Типографика карточки
PT_CARD_NUM = 28
PT_CARD_TITLE = 14
PT_CARD_BODY = 11

# Типографика таблицы
PT_TBL_HEAD = 11
PT_TBL_BODY = 10
PAD_TBL_X = 8
PAD_TBL_Y = 6

# ── Compact mode (уменьшенные gaps при overflow) ──────────────
_compact = False


def _set_compact_mode(on: bool) -> None:
    global _compact
    _compact = on


def _gap() -> int:
    """Текущий gap с учётом compact mode."""
    return GUTTER // 2 if _compact else GUTTER


# ════════════════════════════════════════════════════════════
#  ПОБОЧНЫЙ КОНТЕЙНЕР: связь Node ↔ метаданные блока
# ════════════════════════════════════════════════════════════

@dataclass
class BlockCtx:
    """Контекст блока — связь между stretchable Node и данными GridBlock."""
    node: Node
    block: GridBlock
    text_specs: list[dict] = field(default_factory=list)
    wrapper_nodes: list[dict] = field(default_factory=list)


# ════════════════════════════════════════════════════════════
#  ИЗМЕРИТЕЛИ ТЕКСТА (measure_func для stretchable)
# ════════════════════════════════════════════════════════════

def _make_text_measure(
    text: str, size_pt: float, bold: bool = False, min_h: float = 0.0
):
    """Фабрика measure-функции для текстового листового узла."""
    def measure(node, known_dimensions, available_space):
        kw = known_dimensions.width.value
        aw = available_space.width

        if not isnan(kw):
            w = float(kw)
        elif aw.scale == Scale.POINTS and not isnan(aw.value):
            w = float(aw.value)
        else:
            w = 10000.0

        actual_w, actual_h, _ = measure_block(text, w, size_pt=size_pt, bold=bold)
        h = max(actual_h, min_h)
        return SizePoints(width=actual_w, height=h)

    return measure


# ════════════════════════════════════════════════════════════
#  FLEX_GROW ПО HEIGHT_STRATEGY
# ════════════════════════════════════════════════════════════

def _flex_grow_for(block: GridBlock) -> float:
    """fill-блоки растягиваются, hug — нет."""
    return 1.0 if block.height_strategy == "fill" else 0.0


# ════════════════════════════════════════════════════════════
#  СТРОИТЕЛИ БЛОКОВ
# ════════════════════════════════════════════════════════════

def _build_heading(block: GridBlock) -> BlockCtx:
    """heading: title (24pt bold) + опц. subtitle (12pt) + акцентная линия."""
    c = block.content or {}
    title = (c.get("title") or "").strip()
    subtitle = (c.get("subtitle") or "").strip()

    container = Node(
        flex_direction=FlexDirection.COLUMN,
        gap=6,
        flex_grow=_flex_grow_for(block),
        flex_shrink=1.0,
    )

    text_specs: list[dict] = []

    if title:
        title_node = Node(measure=_make_text_measure(title, PT_HEAD, bold=True))
        container.add(title_node)
        text_specs.append({
            "role": "title", "text": title,
            "size_pt": PT_HEAD, "bold": True,
            "_node": title_node,
        })

    if subtitle:
        sub_node = Node(measure=_make_text_measure(subtitle, PT_SUB))
        container.add(sub_node)
        text_specs.append({
            "role": "subtitle", "text": subtitle,
            "size_pt": PT_SUB, "bold": False,
            "_node": sub_node,
        })

    line_node = Node(size=(60, 3))
    container.add(line_node)
    text_specs.append({
        "role": "accent_line", "text": "", "size_pt": 0, "bold": False,
        "_node": line_node,
    })

    return BlockCtx(node=container, block=block, text_specs=text_specs)


def _build_text(block: GridBlock) -> BlockCtx:
    """text: опц. title (15pt bold) + body или bullets (12pt)."""
    c = block.content or {}
    title = (c.get("title") or "").strip()
    body = (c.get("body") or "").strip()
    bullets = c.get("bullet_points") or []

    container = Node(
        flex_direction=FlexDirection.COLUMN,
        gap=8,
        flex_grow=_flex_grow_for(block),
        flex_shrink=1.0,
    )

    text_specs: list[dict] = []

    if title:
        n = Node(measure=_make_text_measure(title, PT_BTITLE, bold=True))
        container.add(n)
        text_specs.append({
            "role": "title", "text": title,
            "size_pt": PT_BTITLE, "bold": True,
            "_node": n,
        })

    if bullets:
        for i, b in enumerate(bullets):
            b = str(b).strip()
            if not b:
                continue
            n = Node(
                measure=_make_text_measure(b, PT_BODY, min_h=line_height(PT_BODY))
            )
            container.add(n)
            text_specs.append({
                "role": "bullet", "text": b,
                "size_pt": PT_BODY, "bold": False,
                "_node": n,
                "extra": {"bullet_index": i},
            })
    elif body:
        n = Node(
            measure=_make_text_measure(body, PT_BODY, min_h=line_height(PT_BODY))
        )
        container.add(n)
        text_specs.append({
            "role": "body", "text": body,
            "size_pt": PT_BODY, "bold": False,
            "_node": n,
        })

    if not text_specs:
        container = Node(
            min_size=(AUTO, MIN_H_TEXT),
            flex_grow=_flex_grow_for(block),
            flex_shrink=1.0,
        )

    return BlockCtx(node=container, block=block, text_specs=text_specs)


def _build_placeholder(block: GridBlock) -> BlockCtx:
    """chart/visual — заглушка фиксированного размера."""
    node = Node(
        min_size=(AUTO, MIN_H_PLACEHOLDER),
        flex_grow=_flex_grow_for(block),
        flex_shrink=1.0,
    )
    return BlockCtx(node=node, block=block, text_specs=[])


# ════════════════════════════════════════════════════════════
#  КАРТОЧКИ
# ════════════════════════════════════════════════════════════

def _build_card_inner(
    card: dict, card_index: int
) -> tuple[Node, list[dict]]:
    """Одна карточка — flex column с числом/иконкой + title + body."""
    container = Node(
        flex_direction=FlexDirection.COLUMN,
        gap=6,
        padding=PAD_CARD,
        flex_grow=1.0,
        flex_shrink=1.0,
        flex_basis=0,
        min_size=(AUTO, MIN_H_CARD),
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

    container = Node(
        flex_direction=FlexDirection.COLUMN,
        gap=12,
        flex_grow=_flex_grow_for(block),
        flex_shrink=1.0,
        align_items=AlignItems.STRETCH,
        size=(AUTO, AUTO),
    )

    text_specs: list[dict] = []

    if not cards:
        container = Node(
            min_size=(AUTO, MIN_H_CARD),
            flex_grow=_flex_grow_for(block),
            flex_shrink=1.0,
        )
        return BlockCtx(node=container, block=block, text_specs=[])

    wrapper_nodes: list[dict] = []
    for i, card in enumerate(cards):
        card_node, specs = _build_card_inner(card, card_index=i)
        container.add(card_node)
        text_specs.extend(specs)
        wrapper_nodes.append({"kind": "card", "index": i, "node": card_node})

    return BlockCtx(
        node=container, block=block,
        text_specs=text_specs, wrapper_nodes=wrapper_nodes,
    )


# ════════════════════════════════════════════════════════════
#  ТАБЛИЦЫ
# ════════════════════════════════════════════════════════════

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

    container = Node(
        flex_direction=FlexDirection.COLUMN,
        flex_grow=_flex_grow_for(block),
        flex_shrink=1.0,
        min_size=(AUTO, MIN_H_TABLE),
    )
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
            gap=_gap(),
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

_BUILDERS: dict[str, callable] = {
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
#  СБОРКА РЯДА И ВСЕГО СЛАЙДА
# ════════════════════════════════════════════════════════════

def _build_row(row: GridRow) -> tuple[Node, list[BlockCtx]]:
    """Один ряд = flex row, блоки получают точную ширину в % от ряда."""
    row_node = Node(
        flex_direction=FlexDirection.ROW,
        gap=GUTTER,
        align_items=AlignItems.STRETCH,
        size=(AUTO, AUTO),
    )

    total_span = sum(b.col_span for b in row.blocks) or 12
    n = len(row.blocks)
    gutter_pct = 100.0 * _gap() / (SLIDE_W - 2 * MARGIN_H)
    available_pct = 100.0 - (n - 1) * gutter_pct

    ctxs: list[BlockCtx] = []
    for block in row.blocks:
        ctx = _build_block(block)
        col_pct = available_pct * block.col_span / total_span

        slot = Node(
            size=(col_pct * PCT, AUTO),
            flex_shrink=0.0,
            flex_grow=0.0,
            align_items=AlignItems.STRETCH,
            flex_direction=FlexDirection.COLUMN,
        )
        slot.add(ctx.node)
        row_node.add(slot)
        ctxs.append(ctx)

    return row_node, ctxs


def _build_slide_tree(
    plan: LayoutPlanV5,
    strategy: PresentationStrategy,
) -> tuple[Node, list[BlockCtx], Optional[Node], Optional[Node]]:
    """Строит всё дерево слайда."""
    root = Node(
        size=(SLIDE_W, SLIDE_H),
        padding=(MARGIN_V, MARGIN_H, MARGIN_V, MARGIN_H),
        flex_direction=FlexDirection.COLUMN,
        gap=_gap(),
    )

    header_node = None
    if plan.header_type == "A":
        header_node = Node(size=(AUTO, HEADER_A_H))
        root.add(header_node)

    content_root = Node(
        flex_direction=FlexDirection.COLUMN,
        gap=_gap(),
        flex_grow=1.0,
        justify_content=JustifyContent.FLEX_START,
    )
    root.add(content_root)

    all_ctxs: list[BlockCtx] = []
    for row in plan.rows:
        row_node, ctxs = _build_row(row)
        content_root.add(row_node)
        all_ctxs.extend(ctxs)

    footer_node = None
    if plan.needs_footer and plan.footer:
        footer_node = Node(size=(AUTO, FOOTER_H))
        root.add(footer_node)

    return root, all_ctxs, header_node, footer_node


# ════════════════════════════════════════════════════════════
#  ОБХОД ДЕРЕВА: stretchable Node → абсолютные координаты
# ════════════════════════════════════════════════════════════

def _abs_box(node: Node) -> tuple[float, float, float, float]:
    """Абсолютные (от корня слайда) x/y/w/h узла."""
    x, y = 0.0, 0.0
    cur = node
    while cur is not None:
        b = cur.get_box(Edge.BORDER)
        x += b.x
        y += b.y
        cur = cur.parent
    b_self = node.get_box(Edge.BORDER)
    return x, y, b_self.width, b_self.height


def _collect_rendered_texts(
    ctx: BlockCtx,
    block_abs: tuple[float, float, float, float],
) -> list[RenderedText]:
    """Перебирает text_specs, считает абс. позицию и wrap по фактической ширине."""
    out: list[RenderedText] = []

    for spec in ctx.text_specs:
        node: Node = spec["_node"]
        ax, ay, aw, ah = _abs_box(node)

        _, _, lines = measure_block(
            spec["text"], aw, size_pt=spec["size_pt"], bold=spec["bold"]
        )

        out.append(RenderedText(
            role=spec["role"],
            lines=lines,
            size_pt=spec["size_pt"],
            bold=spec["bold"],
            x=round(ax, 1),
            y=round(ay, 1),
            w=round(aw, 1),
            h=round(ah, 1),
            extra=spec.get("extra", {}),
        ))

    # Координаты обёрток (card/cell) в extra
    if ctx.wrapper_nodes:
        wrappers: dict[str, tuple[float, float, float, float]] = {}
        for wn in ctx.wrapper_nodes:
            key = (
                f"{wn['kind']}_{wn.get('index', '')}_"
                f"{wn.get('row', '')}_{wn.get('col', '')}"
            )
            wrappers[key] = _abs_box(wn["node"])

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
    """Главный вход: LayoutPlanV5 → SlideGeometry с точными координатами.

    Если контент не влезает — повторяет layout с уменьшенными gaps.
    """
    root, ctxs, _header, _footer = _build_slide_tree(layout_plan, strategy)
    root.compute_layout()

    # Overflow check
    max_bottom = 0.0
    for ctx in ctxs:
        _, y, _, h = _abs_box(ctx.node)
        max_bottom = max(max_bottom, y + h)

    overflow = max_bottom - (SLIDE_H - MARGIN_V)
    if overflow > 0:
        logger.warning(f"Overflow {overflow:.0f}px — пересобираю с компактными gaps")
        _set_compact_mode(True)
        try:
            root, ctxs, _header, _footer = _build_slide_tree(
                layout_plan, strategy
            )
            root.compute_layout()

            max_bottom = 0.0
            for ctx in ctxs:
                _, y, _, h = _abs_box(ctx.node)
                max_bottom = max(max_bottom, y + h)
            overflow2 = max_bottom - (SLIDE_H - MARGIN_V)
            if overflow2 > 0:
                logger.warning(
                    f"Всё ещё overflow {overflow2:.0f}px после compact mode"
                )
        finally:
            _set_compact_mode(False)

    blocks: list[BlockGeometry] = []
    for ctx in ctxs:
        abs_box = _abs_box(ctx.node)
        x, y, w, h = abs_box

        rendered = _collect_rendered_texts(ctx, abs_box)

        blocks.append(BlockGeometry(
            block_id=ctx.block.block_id,
            x=round(x, 1),
            y=round(y, 1),
            w=round(w, 1),
            h=round(h, 1),
            object_type=ctx.block.semantic_type,
            content=ctx.block.content,
            render=ctx.block.render,
            visual_subtype=ctx.block.visual_subtype,
            rendered_texts=rendered,
        ))

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
        f"LayoutEngine v5: слайд {layout_plan.slide_index} → "
        f"{len(blocks)} блоков"
    )
    return result


# ── Smoke-test ───────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    logging.basicConfig(level=logging.INFO)

    plan = LayoutPlanV5(
        slide_index=0,
        slide_role="content",
        header_type="B",
        style_mode="soft",
        rows=[
            GridRow(
                row_id="r0",
                row_lines=3,
                blocks=[
                    GridBlock(
                        block_id="sb0", col_start=0, col_span=6,
                        semantic_type="heading",
                        content={"title": "Финансовые показатели", "subtitle": "2026 Q1"},
                        height_strategy="hug",
                    ),
                    GridBlock(
                        block_id="sb1", col_start=6, col_span=6,
                        semantic_type="text",
                        content={
                            "title": "Итоги квартала",
                            "bullet_points": [
                                "Выручка выросла на 18% год к году",
                                "Маржинальность EBITDA — 24%",
                                "Запущены 3 новых продукта",
                            ],
                        },
                        height_strategy="hug",
                    ),
                ],
            ),
        ],
        total_lines=6,
    )
    strategy = PresentationStrategy(accent_color="#0066CC")

    def show(label: str, p: LayoutPlanV5) -> None:
        geo = compute_geometry(p, strategy)
        logger.info(
            f"\n══ {label} ══  слайд {geo.slide_index}: {len(geo.blocks)} блоков"
        )
        for b in geo.blocks:
            logger.info(
                f"  [{b.block_id}] {b.object_type}: "
                f"x={b.x} y={b.y} w={b.w} h={b.h}"
            )
            for rt in b.rendered_texts:
                first = rt.lines[0] if rt.lines else ""
                logger.info(
                    f"      {rt.role}: '{first[:40]}' ({len(rt.lines)} стр.) "
                    f"at ({rt.x},{rt.y}) w={rt.w}"
                )

    show("Тест 1: heading + text/bullets", plan)

    plan2 = LayoutPlanV5(
        slide_index=1,
        rows=[
            GridRow(row_id="r0", row_lines=2, blocks=[
                GridBlock(block_id="sb0", col_start=0, col_span=12,
                    semantic_type="heading",
                    content={"title": "Наши преимущества"}, height_strategy="hug"),
            ]),
            GridRow(row_id="r1", row_lines=6, blocks=[
                GridBlock(block_id="sb1", col_start=0, col_span=4,
                    semantic_type="card", height_strategy="fill",
                    content={"cards": [{"number": "01", "title": "Скорость",
                        "body": "Обработка за 2 секунды вместо 5 минут."}]}),
                GridBlock(block_id="sb2", col_start=4, col_span=4,
                    semantic_type="card", height_strategy="fill",
                    content={"cards": [{"number": "02", "title": "Точность",
                        "body": "98% попаданий по бенчмарку GLUE."}]}),
                GridBlock(block_id="sb3", col_start=8, col_span=4,
                    semantic_type="card", height_strategy="fill",
                    content={"cards": [{"number": "03", "title": "Масштаб",
                        "body": "От 10 до 10 000 документов в день."}]}),
            ]),
        ],
        total_lines=8,
    )
    show("Тест 2: 3 карточки в ряд", plan2)

    plan3 = LayoutPlanV5(
        slide_index=2,
        rows=[
            GridRow(row_id="r0", row_lines=8, blocks=[
                GridBlock(block_id="sb0", col_start=0, col_span=12,
                    semantic_type="table", height_strategy="hug",
                    content={
                        "headers": ["Метрика", "2024", "2025", "Δ"],
                        "rows": [
                            ["Выручка, млн ₽", "120", "182", "+52%"],
                            ["EBITDA, млн ₽", "18", "44", "+144%"],
                            ["Клиенты", "230", "410", "+78%"],
                        ],
                    }),
            ]),
        ],
        total_lines=8,
    )
    show("Тест 3: таблица", plan3)