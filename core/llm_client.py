"""Модуль для маршрутизации запросов между облачным Gemini и локальным Ollama."""

import time
import logging
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import LLM_MAX_RETRIES
from core.ollama_client import call_ollama

logger = logging.getLogger(__name__)

def call_llm(prompt: str, model_name: str, image_path: str | None = None, json_mode: bool = False) -> str:
    """Вызывает соответствующий LLM клиент в зависимости от префикса названия модели."""
    logger.info(f"Запрос к LLM: {model_name}, json_mode={json_mode}")

    # Роутинг на локальный Ollama
    if model_name.startswith("ollama/"):
        real_model = model_name.replace("ollama/", "", 1)
        logger.info(f"Перенаправление запроса в Ollama (модель: {real_model})")
        return call_ollama(
            prompt=prompt, 
            model_name=real_model, 
            image_path=image_path, 
            json_mode=json_mode
        )

    # Оригинальная логика для Vertex AI / Gemini
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
        logger.info("Активирован JSON-режим для Gemini")
        
    config = types.GenerateContentConfig(**config_kwargs)
    contents = [prompt]
    
    if image_path is not None:
        try:
            img_path = Path(image_path)
            logger.info(f"Загрузка изображения для Gemini: {img_path}")
            image = Image.open(img_path)
            contents = [prompt, image]
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения {image_path}: {e}")
            raise
            
    for attempt in range(LLM_MAX_RETRIES):
        try:
            logger.info(f"Попытка запроса к Gemini {attempt + 1} из {LLM_MAX_RETRIES}")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            text = response.text
            logger.info(f"Ответ Gemini получен (длина: {len(text)})")
            return text
        except Exception as e:
            logger.warning(f"Ошибка на попытке {attempt + 1}: {e}")
            if attempt == LLM_MAX_RETRIES - 1:
                logger.error("Все попытки вызова Gemini исчерпаны")
                raise
            time.sleep(2 ** attempt)
            
    return ""