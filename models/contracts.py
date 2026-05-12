"""Pydantic-модели (контракты) для обмена данными между компонентами системы PPTX-AI."""

import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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


class ClientConstraints(BaseModel):
    """Ограничения клиента."""
    verbatim_text: bool = False
    preserve_template: bool = False
    allow_slide_split: bool = False
    allow_content_removal: bool = False


class SlideClassificationV2(BaseModel):
    """Выход Classifier (v2)."""
    slide_index: int
    slide_role: str
    objects: list[str] = Field(default_factory=list)
    visual_subtype: Optional[str] = None
    pattern_hint: Optional[str] = None
    header_type: str = "B"
    needs_footer: bool = False
    style_mode: str = "soft"
    series_context: Optional[str] = None
    overload: bool = False
    client_constraints: Optional[ClientConstraints] = None


class ColumnInstruction(BaseModel):
    """Одна колонка в ряду layout-плана."""
    col_id: str = Field(description="c0, c1, c2...")
    grid_span: int = Field(description="Кол-во колонок сетки из 12")
    object_type: str = Field(description="heading, text, card, table, chart, visual")
    visual_subtype: Optional[str] = Field(default=None, description="photo, map, custom_infographic, flowchart, pattern")
    content: dict = Field(default_factory=dict, description="Контент объекта")
    render: str = Field(default="ai", description="ai или external")


class RowInstruction(BaseModel):
    """Один ряд в layout-плане."""
    row_id: str = Field(description="r0, r1, r2...")
    columns: list[ColumnInstruction] = Field(description="Колонки в ряду, span сумма = 12")


class FooterInstruction(BaseModel):
    """Футер слайда."""
    left: str = Field(default="")
    right: str = Field(default="")


class LayoutPlan(BaseModel):
    """Выход Senior Designer v2 — layout-план в терминах сетки."""
    slide_index: int
    header_type: str = Field(default="B", description="A, B, C, none")
    style_mode: str = Field(default="soft", description="strict, soft")
    needs_footer: bool = False
    composition_schema: str = ""
    rows: list[RowInstruction] = Field(default_factory=list)
    footer: Optional[FooterInstruction] = None
    design_notes: str = ""


class DesignedSlide(BaseModel):
    """Выход Junior — готовый SVG код слайда."""
    slide_index: int
    svg_code: str
    generation_time_ms: int = 0


class PresentationStrategy(BaseModel):
    """Стратегия редизайна на уровне всей презентации — формируется один раз Strategy Director."""
    header_type: str = Field(default="floating", description="fixed=прибит к верху, floating=плавает с контентом")
    style_mode: str = Field(default="soft", description="strict, soft")
    accent_color: str = Field(default="#0066CC", description="Акцентный цвет в hex")
    presentation_mode: str = Field(default="formal", description="formal=бизнес/госсектор, technical=финансы/графики, sales=минимум сложности и больше воздуха, report=доклад с крупным шрифтом")
    allow_rewrite: bool = Field(default=False, description="Можно ли Senior Designer перефразировать тексты")