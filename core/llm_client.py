"""Единая обёртка для вызова Gemini API с поддержкой изображений и автоматическими повторами."""

import json
import time
from typing import Optional
from PIL import Image
import google.generativeai as genai

from core.config import GEMINI_API_KEY, LLM_TIMEOUT, LLM_MAX_RETRIES
from core.logger import get_logger

log = get_logger(__name__)
genai.configure(api_key=GEMINI_API_KEY)


def call_llm(prompt: str, model_name: str, image_path: Optional[str] = None, json_mode: bool = False) -> str:
    """Отправляет текстовый или мультимодальный запрос к LLM с механизмом повторных попыток."""
    log.info(f"LLM call: {model_name}, prompt length: {len(prompt)}")
    
    generation_config = {"temperature": 0.3, "max_output_tokens": 8192}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
        
    model = genai.GenerativeModel(model_name, generation_config=generation_config)
    
    content = prompt
    if image_path is not None:
        try:
            image = Image.open(image_path)
            content = [prompt, image]
        except Exception as e:
            log.error(f"Ошибка при загрузке изображения {image_path}: {e}")
            raise
            
    for attempt in range(LLM_MAX_RETRIES):
        try:
            response = model.generate_content(content)
            text = response.text
            log.info(f"LLM response length: {len(text)}")
            return text
        except Exception as e:
            log.warning(f"LLM error (attempt {attempt + 1}): {e}")
            time.sleep(2 ** attempt)
            
    raise RuntimeError(f"LLM failed after {LLM_MAX_RETRIES} attempts")