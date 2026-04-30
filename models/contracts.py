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
    template_used: str = ""
    needs_reverse: list[str] = []


class InspectionResult(BaseModel):
    """Результаты проверки качества (QA) сгенерированного слайда."""
    slide_index: int
    passed: bool
    score: float
    issues: list[str] = []
    suggestions: list[str] = []