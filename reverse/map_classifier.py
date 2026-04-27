import os
import json
import sys
import logging
from pathlib import Path
from typing import Dict
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAP_TYPES: Dict[int, str] = {
    1: "Спутник чистый (растр) + PPTX-объекты",
    2: "Спутник с надписями (растр) + PPTX-объекты",
    3: "Карта мира с выделенными странами",
    4: "Карта страны/города по районам",
    5: "Обычная карта (не спутник) + PPTX-объекты",
    6: "Сложный растр (всё впечатано)",
    7: "Схематическая карта (метро, этажи)",
    8: "Карта с маршрутом А→Б",
    9: "Тепловая карта (heatmap)",
    10: "Карта с фото/иконками",
    11: "Скриншот Google Maps/2GIS/Yandex",
    12: "Инфографика с мини-картой",
    13: "Тематическая/статистическая (пайчарты на карте)",
}

CLASSIFIER_PROMPT: str = (
    "Ты — эксперт по анализу карт в презентациях. Проанализируй изображение и верни JSON со следующими полями:\n"
    "map_type (int 1-13), map_type_name (str), confidence (float 0-1), has_text_on_raster (bool), "
    "has_pptx_objects (bool), region_description (str), recommended_strategy (str), reasoning (str).\n"
    "Соблюдай соответствие типов:\n"
    "1: Спутник чистый + PPTX, 2: Спутник с надписями + PPTX, 3: Карта мира с выделением, "
    "4: Карта региона, 5: Обычная карта + PPTX, 6: Сложный растр, 7: Схематическая, "
    "8: Маршрут А-Б, 9: Тепловая карта, 10: Карта с фото/иконками, 11: Скриншот карт, "
    "12: Инфографика с картой, 13: Статистическая с диаграммами.\n"
    "Верни ответ СТРОГО в формате JSON без markdown-оберток."
)
class MapClassification(BaseModel):
    """Модель данных для классификации карты."""
    map_type: int
    map_type_name: str
    confidence: float
    has_text_on_raster: bool
    has_pptx_objects: bool
    region_description: str
    recommended_strategy: str
    reasoning: str


def classify_map(image_path: str | Path) -> MapClassification:
    """
    Классифицирует изображение карты с помощью Gemini.

    Args:
        image_path: Путь к файлу изображения.

    Returns:
        MapClassification: Объект с результатами анализа.

    Raises:
        ValueError: Если не удалось распарсить JSON или валидация модели не прошла.
        FileNotFoundError: Если файл изображения не найден.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY не установлен в переменных окружения")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

    try:
        image = Image.open(image_path)
    except Exception as e:
        logger.error(f"Ошибка при открытии изображения {image_path}: {e}")
        raise

    try:
        response = model.generate_content([CLASSIFIER_PROMPT, image])
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw_text)
        return MapClassification(**data)
    except Exception as e:
        logger.error(f"Ошибка при обработке контента Gemini: {e}")
        raise ValueError(f"Некорректный формат ответа от Gemini: {e}")


if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_1.jpg"

    try:
        result = classify_map(target_path)
        print(f"Тип: {result.map_type} — {result.map_type_name}")
        print(f"Уверенность: {result.confidence}")
        print(f"Текст на растре: {result.has_text_on_raster}")
        print(f"PPTX-объекты: {result.has_pptx_objects}")
        print(f"Регион: {result.region_description}")
        print(f"Стратегия: {result.recommended_strategy}")
        print(f"Причина: {result.reasoning}")
    except Exception as err:
        logger.error(f"Критическая ошибка обработки: {err}")
