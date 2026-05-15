"""
Pydantic-модели (контракты) для обмена данными между компонентами PPTX-AI v5.

Единый источник истины. Все агенты, движки и рендереры импортируют модели отсюда.
v5: сетка 12×27 клеток, точные height_cells вместо line_budget,
явное позиционирование row_start_cell.
"""

import logging
from typing import Literal, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════
# PARSER
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
    allow_rewrite: bool = Field(
        default=False, description="Можно ли перефразировать тексты"
    )


# ════════════════════════════════════════════════════════
# SEMANTIC EDITOR (Слой 0)
# ════════════════════════════════════════════════════════

class SemanticBlock(BaseModel):
    """Один семантический блок после обработки Semantic Editor.

    height_cells — точная высота в клетках сетки 12×27, измерена через tool
    measure_texts_batch (для текста/таблиц) или посчитана LLM (chart/visual/image).
    proposed_col_span — черновая ширина по минимальным правилам Semantic.
    """
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
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Важность блока для компрессии при overflow (10 = критично)",
    )
    proposed_col_span: int = Field(
        ge=1,
        le=12,
        description="Черновая ширина в колонках (1-12), назначена Semantic по правилам",
    )
    height_cells: int = Field(
        ge=1,
        le=27,
        description="Точная высота блока в клетках сетки 27",
    )


class SemanticSlide(BaseModel):
    """Выход Semantic Editor — очищенный контент одного слайда."""
    slide_index: int
    blocks: list[SemanticBlock] = Field(default_factory=list)
    total_height_cells: int = Field(
        default=0,
        description="Сумма height_cells всех блоков + gaps. Должно быть ≤ GRID_ROWS (27)",
    )


# ════════════════════════════════════════════════════════
# SPATIAL ARCHITECT (Слой 1) — клеточная сетка 12×27
# ════════════════════════════════════════════════════════

class GridBlock(BaseModel):
    """Один блок в клеточной сетке 12×27.

    LLM (Spatial Architect) заполняет: block_id, row_start_cell, col_start,
    col_span, height_cells, render.
    Python (enrich) дополняет: semantic_type, content, visual_subtype
    — копирует из SemanticBlock по block_id.
    """
    block_id: str = Field(description="Ссылка на SemanticBlock.block_id")
    row_start_cell: int = Field(
        ge=0,
        le=26,
        description="Стартовая клетка по вертикали (0-26)",
    )
    col_start: int = Field(
        ge=0,
        le=11,
        description="Стартовая колонка (0-11)",
    )
    col_span: int = Field(
        ge=1,
        le=12,
        description="Ширина в колонках (1-12)",
    )
    height_cells: int = Field(
        ge=1,
        le=27,
        description="Высота блока в клетках (1-27)",
    )
    render: Literal["ai", "external"] = Field(
        default="ai",
        description="ai — SVG Renderer; external — заглушка (chart/photo/map)",
    )
    # Поля ниже заполняются orchestrator на Enrich, НЕ LLM
    semantic_type: Literal[
        "heading", "text", "card", "table", "chart", "visual"
    ] = Field(default="text", description="Тип контента (из SemanticBlock)")
    content: dict = Field(
        default_factory=dict,
        description="Контент блока (копия из SemanticBlock.content)",
    )
    visual_subtype: Optional[str] = Field(
        default=None,
        description="photo / map / flowchart / pattern / custom_infographic",
    )


class GridRow(BaseModel):
    """Один горизонтальный ряд слайда в клеточной сетке.

    Сумма col_span всех блоков строки должна равняться 12.
    height_cells ряда = максимум height_cells среди блоков ряда.
    """
    row_id: str = Field(description="r0, r1, r2…")
    row_start_cell: int = Field(
        ge=0,
        le=26,
        description="Стартовая клетка ряда по вертикали",
    )
    height_cells: int = Field(
        ge=1,
        le=27,
        description="Высота ряда в клетках (макс. из height_cells блоков)",
    )
    blocks: list[GridBlock] = Field(
        description="Блоки в ряду. Сумма col_span = 12.",
    )


class FooterInstruction(BaseModel):
    """Футер слайда."""
    left: str = Field(default="")
    right: str = Field(default="")


class LayoutPlanV5(BaseModel):
    """Выход Spatial Architect v5 — полный layout-план слайда в клетках 12×27.

    total_height_cells = сумма height_cells всех рядов + gap между ними.
    Validator проверяет: total_height_cells ≤ GRID_ROWS (27).
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
    footer: Optional[FooterInstruction] = None
    total_height_cells: int = Field(
        default=0,
        description="Сумма height_cells всех рядов + gaps. Validator: ≤ 27.",
    )
    design_notes: str = ""


# ════════════════════════════════════════════════════════
# LAYOUT ENGINE
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
    block_id: str
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
# SVG RENDERER
# ════════════════════════════════════════════════════════

class DesignedSlide(BaseModel):
    """Выход SVG Renderer — готовый SVG код слайда."""
    slide_index: int
    svg_code: str
    generation_time_ms: int = 0