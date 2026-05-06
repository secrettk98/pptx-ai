"""Pydantic-модели (контракты) для обмена данными между компонентами системы PPTX-AI."""

import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SlideInfo(BaseModel):
    """Базовая физическая и контентная информация о конкретном слайде."""
    slide_index: int
    width: float
    height: float
    texts: list[str] = []
    image_count: int = 0
    shape_count: int = 0


class PresentationStructure(BaseModel):
    """Общая структура презентации, включающая информацию по всем слайдам."""
    filename: str
    slide_count: int
    slides: list[SlideInfo]


class SlideClassification(BaseModel):
    """Определенный ИИ тип слайда и наличие специфичных визуальных элементов."""
    slide_index: int
    slide_type: str
    has_chart: bool = False
    has_map: bool = False
    has_flowchart: bool = False
    has_table: bool = False
    confidence: float = 0.0


class PresentationStrategy(BaseModel):
    """Утвержденная стратегия и стиль для редизайна всей презентации."""
    presentation_type: str
    audience: str
    key_message: str
    color_accent: str
    style: str = "corporate_strict"
    notes: str = ""


class SlideBrief(BaseModel):
    """Инструкции (бриф) для генерации дизайна отдельного слайда."""
    slide_index: int
    layout_name: str
    headline: str
    key_points: list[str] = []
    visual_hint: str = ""
    remove: list[str] = []
    priority_order: list[str] = []


class DesignedSlide(BaseModel):
    """Сгенерированный макет слайда в формате SVG."""
    slide_index: int
    svg_code: str
    generation_time_ms: int = 0


# === ФАЗА 4.1: JSON_FINAL контракты ===

class ElementInfo(BaseModel):
    """Один элемент внутри смысловой группы."""
    type: str = Field(description="text, icon, image, table, map, chart, scheme, shape")
    subtype: str = Field(default="", description="title, subtitle, body, numbered_list, bullet_list, photo, logo, bar_chart, pie_chart, line_chart, geo_map, flowchart и т.д.")
    content: str = Field(default="", description="Текстовое содержимое или описание элемента")
    style: dict = Field(default_factory=dict, description="font_size, bold, font_color, align и т.д.")
    rows: Optional[int] = Field(default=None, description="Кол-во строк для таблиц")
    cols: Optional[int] = Field(default=None, description="Кол-во столбцов для таблиц")


class GroupPosition(BaseModel):
    """Примерная позиция группы на слайде в пикселях (1280x720)."""
    x: int
    y: int
    w: int
    h: int


class SlideGroup(BaseModel):
    """Смысловая группа объектов на слайде."""
    group_id: str = Field(description="g0, g1, g2...")
    role: str = Field(description="title, data_table, info_block, image_block, map, chart, scheme, content, decoration")
    zone: str = Field(description="top-left, top-center, top-right, middle-left, center, middle-right, bottom-left, bottom-center, bottom-right, left, right, full")
    position: GroupPosition
    elements: list[ElementInfo]
    reverse_type: Optional[str] = Field(default=None, description="map, chart, scheme, image — если группе нужен reverse")
    reverse_action: Optional[str] = Field(default=None, description="keep, regenerate, remove")
    reverse_reason: str = Field(default="", description="Почему нужен reverse")


class ColorPalette(BaseModel):
    """Цветовая палитра слайда."""
    background: str = Field(default="#FFFFFF")
    primary: str = Field(default="#0066CC", description="Фирменный/акцентный цвет")
    text_primary: str = Field(default="#1A1A1A")
    text_secondary: str = Field(default="#666666")


class SlideClassificationFinal(BaseModel):
    """JSON_FINAL — итоговая классификация слайда после объединения Vision + Parser."""
    slide_index: int
    slide_type: str = Field(description="title, content, section, chart, map, mixed, closing")
    complexity: str = Field(description="simple, medium, complex")
    color_palette: ColorPalette
    groups: list[SlideGroup]
    reverse_summary: list[str] = Field(default_factory=list, description="Сводный список reverse-типов для оркестратора")

# === Обогащённый парсер ===

class ShapeStyle(BaseModel):
    """Визуальные стили элемента."""
    font_family: str = ""
    font_size: Optional[float] = None
    font_color: str = ""
    bold: bool = False
    italic: bool = False
    align: str = ""
    fill_color: str = ""
    line_color: str = ""

class ParsedShape(BaseModel):
    """Один элемент слайда, извлечённый парсером."""
    shape_id: int
    shape_type: str = Field(description="textbox, picture, table, rectangle, oval, freeform, group, connector, placeholder, other")
    name: str = ""
    position: GroupPosition
    rotation: float = 0.0
    texts: list[str] = []
    style: ShapeStyle = Field(default_factory=ShapeStyle)
    table_data: Optional[list[list[str]]] = Field(default=None, description="Содержимое таблицы [строки][столбцы]")
    image_index: Optional[int] = Field(default=None, description="Порядковый номер картинки на слайде")

class ParsedSlide(BaseModel):
    """Обогащённые данные одного слайда."""
    slide_index: int
    width: float
    height: float
    background_color: str = ""
    shapes: list[ParsedShape] = []

class ParsedPresentation(BaseModel):
    """Обогащённая структура всей презентации."""
    filename: str
    slide_count: int
    slides: list[ParsedSlide]