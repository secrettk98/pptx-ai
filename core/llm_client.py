"""Модуль для вызовов LLM: синхронный, async, с system_instruction."""

import asyncio
import time
import logging
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import LLM_MAX_RETRIES
from core.ollama_client import call_ollama

logger = logging.getLogger(__name__)


def _make_client():
    """Создаёт Vertex AI клиент."""
    return genai.Client(
        vertexai=True,
        project="powermagic",
        location="us-central1"
    )


def _make_config(json_mode: bool = False, temperature: float = 0.3) -> types.GenerateContentConfig:
    """Создаёт конфиг для генерации."""
    kwargs = {
        "temperature": temperature,
        "max_output_tokens": 65536,
    }
    if json_mode:
        kwargs["response_mime_type"] = "application/json"
    return types.GenerateContentConfig(**kwargs)


def call_llm(
    prompt: str,
    model_name: str,
    image_path: str | list[str] | None = None,
    json_mode: bool = False,
    system_instruction: str | None = None
) -> str:
    """Синхронный вызов LLM. image_path может быть одной строкой или списком путей (мульти-изображения)."""
    logger.info(f"Запрос к LLM: {model_name}, json_mode={json_mode}")

    # Роутинг на Ollama (только одно изображение)
    if model_name.startswith("ollama/"):
        real_model = model_name.replace("ollama/", "", 1)
        single_img = image_path if isinstance(image_path, str) else None
        return call_ollama(prompt=prompt, model_name=real_model,
                           image_path=single_img, json_mode=json_mode)

    client = _make_client()
    config = _make_config(json_mode=json_mode)

    if system_instruction:
        config.system_instruction = system_instruction

    contents = [prompt]
    if image_path is not None:
        paths = image_path if isinstance(image_path, (list, tuple)) else [image_path]
        for p in paths:
            try:
                image = Image.open(Path(p))
                contents.append(image)
            except Exception as e:
                logger.error(f"Ошибка загрузки изображения {p}: {e}")
                raise
        logger.info(f"Передано {len(paths)} изображений в запрос")

    for attempt in range(LLM_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model_name, contents=contents, config=config
            )
            text = response.text
            logger.info(f"Ответ получен ({len(text)} символов)")
            return text
        except Exception as e:
            logger.warning(f"Попытка {attempt+1}/{LLM_MAX_RETRIES} не удалась: {e}")
            if attempt == LLM_MAX_RETRIES - 1:
                raise
            time.sleep(2 ** attempt)
    return ""


async def call_llm_async(
    prompt: str,
    model_name: str,
    json_mode: bool = False,
    system_instruction: str | None = None,
    semaphore: asyncio.Semaphore | None = None
) -> str:
    """Async вызов LLM. Semaphore ограничивает параллельность."""

    async def _call():
        client = _make_client()
        config = _make_config(json_mode=json_mode)
        if system_instruction:
            config.system_instruction = system_instruction

        for attempt in range(LLM_MAX_RETRIES):
            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents=[prompt],
                    config=config
                )
                text = response.text
                logger.info(f"Async ответ получен ({len(text)} символов)")
                return text
            except Exception as e:
                logger.warning(f"Async попытка {attempt+1}: {e}")
                if attempt == LLM_MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return ""

    if semaphore:
        async with semaphore:
            return await _call()
    return await _call()