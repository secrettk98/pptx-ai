"""
Pydantic-модели (контракты) для обмена данными между компонентами PPTX-AI v5.

Ключевые изменения v5:
- Добавлены GridRow / GridBlock (12-колоночная сетка, height_strategy hug/fill).
- ColumnInstruction / RowInstruction сохранены для обратной совместимости с LayoutEngine v5.
- Добавлены контракты Semantic Editor и Router.
"""

import logging
from typing import Literal, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════
# ПАРСЕР
# ════════════════════════════════════════════════════════

class GroupPosition(BaseModel):
    """Позиция объекта на слайде в пикселях."""
    x: float
    y: float
    w: float
    h: float


class ShapeStyle(BaseModel):
    """Стилизованные параметры шейпа."""
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    font_color: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    align: Optional[str] = None
    fill_color: Optional[str] = None
    line_color: Optional[str] = None


class ParsedShape(BaseModel):
    """Один шейп из парсера."""
    shape_id: str
    shape_type: str
    name: str
    position: GroupPosition
    rotation: float = 0.0
    texts: list[str] = Field(default_factory=list)
    style: Optional[ShapeStyle] = None
    table_data: Optional[list[list[str]]] = None
    image_index: Optional[int] = None


class ParsedSlide(BaseModel):
    """Один слайд из парсера."""
    slide_index: int
    width: float
    height: float
    background_color: Optional[str] = None
    shapes: list[ParsedShape] = Field(default_factory=list)


class ParsedPresentation(BaseModel):
    """Вся разобранная презентация."""
    filename: str
    slide_count: int
    slides: list[ParsedSlide] = Field(default_factory=list)


# ════════════════════════════════════════════════════════
# STRATEGY
# ════════════════════════════════════════════════════════

class PresentationStrategy(BaseModel):
    """Стратегия редизайна — формируется один раз Strategy Director."""
    header_type: str = Field(default="floating", description="fixed / floating")
    style_mode: str = Field(default="soft", description="strict / soft")
    accent_color: str = Field(default="#0066CC", description="Акцентный цвет hex")
    presentation_mode: str = Field(
        default="formal", description="formal / technical / sales / report"
    )
    allow_rewrite: bool = Field(default=False, description="Можно ли перефразировать тексты")


# ════════════════════════════════════════════════════════
# SEMANTIC EDITOR (Левое полушарие — Слой 0)
# ════════════════════════════════════════════════════════

class SemanticBlock(BaseModel):
    """Один семантический блок после обработки Semantic Editor."""
    block_id: str = Field(description="sb0, sb1, sb2…")
    semantic_type: Literal[
        "heading", "text", "card", "table", "chart", "visual"
    ] = Field(description="Тип контента")
    content: dict = Field(
        default_factory=dict,
        description="Чистый контент: title/subtitle/body/bullets/cards/headers/rows",
    )
    visual_subtype: Optional[str] = Field(
        default=None,
        description="photo / map / flowchart / pattern / custom_infographic",
    )
    line_budget: int = Field(
        default=0,
        description="Оценка кол-ва строк (считает Semantic Editor для Spatial Architect)",
    )


class SemanticSlide(BaseModel):
    """Выход Semantic Editor — очищенный контент одного слайда."""
    slide_index: int
    blocks: list[SemanticBlock] = Field(default_factory=list)
    total_lines: int = Field(
        default=0, description="Сумма line_budget всех блоков"
    )


# ════════════════════════════════════════════════════════
# SPATIAL ARCHITECT — СЛОЙ 1 (GridRow / GridBlock)
# ════════════════════════════════════════════════════════

HeightStrategy = Literal["hug", "fill"]
"""
hug  — блок сжимается до размера содержимого (stretchable: flex_grow=0, size=AUTO).
fill — блок растягивается на оставшееся пространство (stretchable: flex_grow=1).
"""


class GridBlock(BaseModel):
    """
    Один блок в 12-колоночной сетке.

    col_start + col_span <= 12.
    Каждый блок точно соответствует одному SemanticBlock.
    """
    block_id: str = Field(description="Ссылка на SemanticBlock.block_id")
    col_start: int = Field(ge=0, le=11, description="Стартовая колонка (0-based)")
    col_span: int = Field(ge=1, le=12, description="Ширина в колонках (1-12)")
    height_strategy: HeightStrategy = Field(
        default="hug",
        description="hug — высота по контенту, fill — растянуть на остаток",
    )
    render: Literal["ai", "external"] = Field(
        default="ai",
        description="ai — SVG Renderer; external — заглушка (chart/photo/map)",
    )


class GridRow(BaseModel):
    """
    Один горизонтальный ряд слайда.

    Сумма col_span всех блоков строки ДОЛЖНА равняться 12.
    row_lines — оценочное кол-во строк, которые займёт этот ряд (для budget-контроля).
    """
    row_id: str = Field(description="r0, r1, r2…")
    blocks: list[GridBlock] = Field(
        description="Блоки в ряду. Сумма col_span = 12."
    )
    row_lines: int = Field(
        default=0,
        description="Оценка строк ряда (передаётся от Spatial Architect)",
    )


class LayoutPlanV5(BaseModel):
    """
    Выход Spatial Architect v5.

    Отличие от LayoutPlan v4:
    - rows: list[GridRow] вместо list[RowInstruction]
    - Явные col_start/col_span вместо grid_span
    - Явная height_strategy (hug/fill) вместо неявного flex_grow
    - total_lines — Architect обязан уложиться в LINE_BUDGET (20-25 строк)
    """
    slide_index: int
    slide_role: Literal[
        "title", "section", "content", "closing", "blank"
    ] = "content"
    header_type: Literal["A", "B", "C", "none"] = "B"
    style_mode: Literal["strict", "soft"] = "soft"
    needs_footer: bool = False
    composition_schema: Literal["A", "B", "C", "D"] = "A"
    rows: list[GridRow] = Field(default_factory=list)
    footer: Optional["FooterInstruction"] = None
    total_lines: int = Field(
        default=0,
        description="Сумма row_lines всех рядов. Validator: должно быть <= 25.",
    )
    design_notes: str = ""


# ════════════════════════════════════════════════════════
# ОБРАТНАЯ СОВМЕСТИМОСТЬ v4 (LayoutEngine v5 использует их)
# ════════════════════════════════════════════════════════

class ColumnInstruction(BaseModel):
    """Одна колонка в ряду layout-плана (v4, совместимость с LayoutEngine v5)."""
    col_id: str = Field(description="c0, c1, c2…")
    grid_span: int = Field(description="Кол-во колонок сетки из 12")
    object_type: str = Field(
        description="heading, text, card, table, chart, visual"
    )
    visual_subtype: Optional[str] = Field(
        default=None,
        description="photo, map, flowchart, pattern, custom_infographic",
    )
    content: dict = Field(default_factory=dict, description="Контент объекта")
    render: str = Field(default="ai", description="ai / external")


class RowInstruction(BaseModel):
    """Один ряд в layout-плане (v4, совместимость с LayoutEngine v5)."""
    row_id: str = Field(description="r0, r1, r2…")
    columns: list[ColumnInstruction] = Field(
        description="Колонки в ряду, span сумма = 12"
    )


class FooterInstruction(BaseModel):
    """Футер слайда."""
    left: str = Field(default="")
    right: str = Field(default="")


class LayoutPlan(BaseModel):
    """Выход Architect v4 — полный план слайда (обратная совместимость)."""
    slide_index: int
    slide_role: str = Field(default="content")
    header_type: str = Field(default="B", description="A / B / C / none")
    style_mode: str = Field(default="soft", description="strict / soft")
    needs_footer: bool = False
    composition_schema: str = Field(default="A", description="A / B / C / D")
    rows: list[RowInstruction] = Field(default_factory=list)
    footer: Optional[FooterInstruction] = None
    design_notes: str = ""


# ════════════════════════════════════════════════════════
# LAYOUT ENGINE (без изменений)
# ════════════════════════════════════════════════════════

class RenderedText(BaseModel):
    """Готовый к отрисовке текстовый фрагмент после wrap."""
    role: str = Field(
        description=(
            "title / subtitle / body / bullet / "
            "card_title / card_body / cell_header / cell_body"
        )
    )
    lines: list[str] = Field(default_factory=list, description="Строки после word-wrap")
    size_pt: float = 12.0
    bold: bool = False
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    extra: dict = Field(
        default_factory=dict,
        description=(
            "Доп. данные: row_index/col_index для таблиц, "
            "card_index для карточек и т.п."
        ),
    )


class BlockGeometry(BaseModel):
    """Точные пиксельные координаты одного блока после LayoutEngine."""
    col_id: str
    x: float
    y: float
    w: float
    h: float
    object_type: str
    content: dict = Field(default_factory=dict)
    render: str = "ai"
    visual_subtype: Optional[str] = None
    rendered_texts: list[RenderedText] = Field(
        default_factory=list,
        description="Готовые тексты после wrap",
    )


class SlideGeometry(BaseModel):
    """Полная геометрия одного слайда — выход LayoutEngine."""
    slide_index: int
    slide_role: str = "content"
    header_type: str = "B"
    style_mode: str = "soft"
    accent_color: str = "#0066CC"
    blocks: list[BlockGeometry] = Field(default_factory=list)
    footer: Optional[FooterInstruction] = None


# ════════════════════════════════════════════════════════
# SVG RENDERER (без изменений)
# ════════════════════════════════════════════════════════

class DesignedSlide(BaseModel):
    """Выход SVG Renderer — готовый SVG код слайда."""
    slide_index: int
    svg_code: str
    generation_time_ms: int = 0


# Разрешаем forward-reference FooterInstruction в LayoutPlanV5
LayoutPlanV5.model_rebuild()