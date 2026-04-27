import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel

from reverse.map_classifier import classify_map, MapClassification
from reverse.map_layer_splitter import split_slide_layers, LayerSplit

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MAP_STRATEGIES: Dict[int, Dict[str, Any]] = {
    1: {"replace_bg": "nano_banana", "redesign_objects": True, "vectorize": False},
    2: {"replace_bg": "mapbox", "redesign_objects": True, "vectorize": False},
    3: {"replace_bg": "svg_world", "redesign_objects": True, "vectorize": False},
    4: {"replace_bg": "svg_country", "redesign_objects": True, "vectorize": False},
    5: {"replace_bg": "mapbox", "redesign_objects": True, "vectorize": False},
    6: {"replace_bg": "nano_banana", "redesign_objects": False, "vectorize": True},
    7: {"replace_bg": "keep", "redesign_objects": True, "vectorize": False},
    8: {"replace_bg": "mapbox", "redesign_objects": True, "vectorize": False},
    9: {"replace_bg": "mapbox", "redesign_objects": True, "vectorize": False},
    10: {"replace_bg": "mapbox", "redesign_objects": True, "vectorize": False},
    11: {"replace_bg": "mapbox", "redesign_objects": True, "vectorize": False},
    12: {"replace_bg": "detect_subtype", "redesign_objects": True, "vectorize": False},
    13: {"replace_bg": "programmatic", "redesign_objects": True, "vectorize": False},
}


class MapPipelineResult(BaseModel):
    """Результат полного пайплайна обработки карты."""
    slide_number: int
    classification: Optional[MapClassification] = None
    layer_split: Optional[LayerSplit] = None
    new_background_path: Optional[str] = None
    redesigned_objects: Optional[list] = None
    final_slide_path: Optional[str] = None
    status: str = "completed"
    errors: list[str] = []


def process_map_slide(
    pptx_path: str | Path,
    slide_number: int = 1,
    accent_color: str = "#0066CC",
    output_dir: str | Path | None = None
) -> MapPipelineResult:
    """Оркестратор редизайна карты для заданного слайда."""
    out_path = Path(output_dir or "projects/test_map/output")
    out_path.mkdir(parents=True, exist_ok=True)

    result = MapPipelineResult(slide_number=slide_number)

    # Шаг 1: Разделение слоёв
    try:
        logger.info("Шаг 1/5: Разделение слоёв...")
        result.layer_split = split_slide_layers(pptx_path, slide_number, out_path)
        if not result.layer_split.background:
            result.errors.append("Подложка не найдена")
    except Exception as e:
        err_msg = f"Ошибка при разделении слоев: {e}"
        logger.error(err_msg)
        result.errors.append(err_msg)

    # Шаг 2: Классификация
    try:
        logger.info("Шаг 2/5: Классификация карты...")
        if result.layer_split and result.layer_split.background_image_path:
            result.classification = classify_map(result.layer_split.background_image_path)
        else:
            result.errors.append("Отсутствует путь к фону для классификации")
    except Exception as e:
        err_msg = f"Ошибка при классификации: {e}"
        logger.error(err_msg)
        result.errors.append(err_msg)

    # Шаг 3: Определение стратегии
    try:
        logger.info("Шаг 3/5: Определение стратегии...")
        if result.classification:
            map_type = result.classification.map_type
            strategy = MAP_STRATEGIES.get(map_type, MAP_STRATEGIES[6])
            logger.info(f"Тип {map_type}: стратегия подложки = {strategy['replace_bg']}")
    except Exception as e:
        logger.error(f"Ошибка при выборе стратегии: {e}")
        result.errors.append("Ошибка выбора стратегии")

    # Шаг 4-5: Заглушки для последующих модулей
    logger.info("Шаг 4/5: Замена подложки... (TODO: map_background.py)")
    logger.info("Шаг 5/5: Редизайн объектов... (TODO: map_objects_redesign.py)")

    return result


if __name__ == "__main__":
    pptx = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    slide = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    accent = sys.argv[3] if len(sys.argv) > 3 else "#0066CC"

    res = process_map_slide(pptx, slide, accent)

    print("=== MAP PIPELINE RESULT ===")
    print(f"Слайд: {res.slide_number}")
    if res.classification:
        print(f"Тип карты: {res.classification.map_type} — {res.classification.map_type_name}")
        print(f"Уверенность: {res.classification.confidence}")
        print(f"Стратегия подложки: {MAP_STRATEGIES[res.classification.map_type]['replace_bg']}")
    print(f"Объектов на карте: {len(res.layer_split.objects) if res.layer_split else 0}")
    print(f"Ошибки: {res.errors if res.errors else 'нет'}")
    print(f"Статус: {res.status}")