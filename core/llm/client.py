"""Модуль для вызовов LLM: синхронный, async, с system_instruction."""

import asyncio
import time
import logging
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types
from typing import Any, Callable

from core.config import LLM_MAX_RETRIES, MAX_TOOL_CALLS_PER_SLIDE
from core.llm.ollama import call_ollama

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

def call_llm_with_tools(
    prompt: str,
    model_name: str,
    tools: list[types.FunctionDeclaration],
    handlers: dict[str, Callable[..., dict]],
    image_path: str | list[str] | None = None,
    system_instruction: str | None = None,
    json_mode: bool = False,
    max_tool_calls: int = 5,
    temperature: float = 0.3,
) -> str:
    """Вызов LLM с function calling loop.

    LLM может вызывать tools несколько раз. После каждого function_call
    Python выполняет handler и возвращает результат в диалог.
    Лимит max_tool_calls защищает от бесконечного цикла.
    Возвращает финальный текстовый ответ модели (после всех tool calls).
    """
    logger.info(f"Запрос к LLM с tools: {model_name}, tools={[t.name for t in tools]}")

    if model_name.startswith("ollama/"):
        raise NotImplementedError("Function calling не поддерживается для Ollama")

    client = _make_client()
    config = _make_config(json_mode=json_mode, temperature=temperature)
    config.tools = [types.Tool(function_declarations=tools)]
    if system_instruction:
        config.system_instruction = system_instruction

    # Сборка начального contents
    user_parts: list[Any] = [types.Part.from_text(text=prompt)]
    if image_path is not None:
        paths = image_path if isinstance(image_path, (list, tuple)) else [image_path]
        for p in paths:
            try:
                img_bytes = Path(p).read_bytes()
                user_parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
            except OSError as e:
                logger.error(f"Ошибка загрузки изображения {p}: {e}")
                raise
        logger.info(f"Передано {len(paths)} изображений в tool-запрос")

    contents: list[types.Content] = [types.Content(role="user", parts=user_parts)]

    for call_idx in range(max_tool_calls + 1):
        try:
            response = client.models.generate_content(
                model=model_name, contents=contents, config=config
            )
        except Exception as e:
            logger.error(f"Ошибка LLM на итерации {call_idx}: {e}")
            raise

        candidate = response.candidates[0] if response.candidates else None
        if candidate is None or not candidate.content or not candidate.content.parts:
            logger.warning("Пустой ответ от LLM")
            return response.text or ""

        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]

        if not function_calls:
            text = response.text or ""
            logger.info(f"Финальный ответ получен ({len(text)} символов, tool calls={call_idx})")
            return text

        if call_idx >= max_tool_calls:
            raise RuntimeError(
                f"Превышен лимит tool calls ({max_tool_calls}). "
                f"LLM продолжает звать функции: {[fc.name for fc in function_calls]}"
            )

        # Добавляем ответ модели (с function_call) в историю
        contents.append(candidate.content)

        # Выполняем все function_call в этом ходе и собираем function_response
        response_parts: list[types.Part] = []
        for fc in function_calls:
            handler = handlers.get(fc.name)
            if handler is None:
                logger.error(f"Нет хендлера для tool '{fc.name}'")
                result = {"error": f"Unknown tool: {fc.name}"}
            else:
                args = dict(fc.args) if fc.args else {}
                logger.info(f"Tool call #{call_idx + 1}: {fc.name}(args_keys={list(args.keys())})")
                try:
                    result = handler(**args)
                except (TypeError, ValueError, KeyError) as e:
                    logger.error(f"Ошибка handler '{fc.name}': {e}")
                    result = {"error": str(e)}
            response_parts.append(
                types.Part.from_function_response(name=fc.name, response=result)
            )

        contents.append(types.Content(role="user", parts=response_parts))

    return ""