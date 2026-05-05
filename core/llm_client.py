"""Единая обёртка для вызова Gemini API через Vertex AI с поддержкой изображений и повторами."""

import time
import logging
from typing import Optional
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import LLM_TIMEOUT, LLM_MAX_RETRIES

logger = logging.getLogger(__name__)


def call_llm(prompt: str, model_name: str, image_path: Optional[str] = None, json_mode: bool = False) -> str:
    """Отправляет текстовый или мультимодальный запрос к LLM с механизмом повторных попыток."""
    logger.info(f"Начинаем вызов LLM (Vertex AI): {model_name}, длина промпта: {len(prompt)}")
    
    client = genai.Client(
        vertexai=True,
        project="powermagic",
        location="us-central1"
    )
    
    config_kwargs = {
        "temperature": 0.3,
        "max_output_tokens": 65536,
    }
    
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
        logger.info("Активирован режим JSON-ответа")
        
    config = types.GenerateContentConfig(**config_kwargs)
    contents = [prompt]
    
    if image_path is not None:
        try:
            img_path = Path(image_path)
            logger.info(f"Чтение изображения из файла: {img_path}")
            image = Image.open(img_path)
            contents = [prompt, image]
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения {image_path}: {e}")
            raise
            
    for attempt in range(LLM_MAX_RETRIES):
        try:
            logger.info(f"Попытка отправки запроса {attempt + 1} из {LLM_MAX_RETRIES}")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            text = response.text
            logger.info(f"Получен успешный ответ LLM, длина текста: {len(text)}")
            return text
        except Exception as e:
            logger.warning(f"Ошибка LLM (попытка {attempt + 1}): {e}")
            time.sleep(2 ** attempt)
            
    logger.error(f"LLM не ответила после {LLM_MAX_RETRIES} попыток")
    raise RuntimeError(f"LLM failed after {LLM_MAX_RETRIES} attempts")