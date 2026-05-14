"""Обёртка для взаимодействия с локальным API Ollama."""

import base64
import logging
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/chat"
MAX_RETRIES = 3
TIMEOUT_SECONDS = 300

def _encode_image(image_path: str) -> str:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл изображения не найден: {path}")
    
    with path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _build_payload(prompt: str, model_name: str, image_path: str | None, json_mode: bool) -> dict[str, Any]:
    
    if json_mode:
        prompt += "\nRespond strictly in JSON format, no markdown."
        
    message: dict[str, Any] = {
        "role": "user",
        "content": prompt
    }
    
    if image_path:
        message["images"] = [_encode_image(image_path)]
        logger.info(f"Изображение {image_path} успешно закодировано")
        
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": [message],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 8192
        },
        "think": False
    }
        
    return payload

def call_ollama(prompt: str, model_name: str, image_path: str | None = None, json_mode: bool = False) -> str:
    logger.info(f"Начало вызова Ollama API (модель: {model_name}, json_mode: {json_mode})")
    
    try:
        payload = _build_payload(prompt, model_name, image_path, json_mode)
    except Exception as e:
        logger.error(f"Ошибка при формировании тела запроса: {e}")
        raise
        
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Отправка POST запроса к {OLLAMA_API_URL} (попытка {attempt}/{MAX_RETRIES})")
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            
            result = response.json()["message"]["content"]
            logger.info("Ответ от Ollama успешно получен")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Сетевая ошибка при вызове Ollama: {e}")
            if attempt == MAX_RETRIES:
                logger.error("Исчерпан лимит попыток подключения к Ollama")
                raise RuntimeError(f"Не удалось получить ответ от Ollama после {MAX_RETRIES} попыток: {e}") from e
            
            delay = 2 ** attempt
            logger.info(f"Ожидание {delay} секунд перед повторной попыткой...")
            time.sleep(delay)
            
    return ""