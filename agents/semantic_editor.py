"""
Semantic Editor (Слой 0) — анализирует ParsedSlide, очищает контент,
определяет смысловые блоки и возвращает SemanticSlide.
Модель: Gemini 2.5 Pro (Chain of Thought via <thinking>).
Не принимает никаких дизайн-решений.
"""

import json
import logging
import re
from pathlib import Path

from core.config import MODEL_BRAIN, PROMPTS_DIR
from core.llm.client import call_llm
from core.llm.normalize import normalize_for_model
from models.contracts import PresentationStrategy, SemanticBlock, SemanticSlide

logger = logging.getLogger(__name__)

PROMPT_FILE: Path = PROMPTS_DIR / "semantic_editor.md"


def _load_system_prompt() -> str:
    """Читает системный промпт Semantic Editor из файла."""
    try:
        return PROMPT_FILE.read_text(encoding="utf-8")
    except OSError as e:
        logger.error(f"Не удалось прочитать промпт {PROMPT_FILE}: {e}")
        raise


def _build_user_message(
    parsed_slide: dict,
    strategy: PresentationStrategy,
    slide_index: int,
) -> str:
    """Формирует user-сообщение из ParsedSlide + стратегии."""
    return (
        f"# SLIDE {slide_index}\n\n"
        f"## Strategy context\n"
        f"presentation_mode={strategy.presentation_mode}, "
        f"allow_rewrite={strategy.allow_rewrite}, "
        f"style_mode={strategy.style_mode}\n\n"
        f"## ParsedSlide (JSON)\n"
        f"{json.dumps(parsed_slide, ensure_ascii=False, indent=2)}"
    )


def _strip_thinking(raw: str) -> str:
    """Вырезает <thinking>…</thinking> — оставляет только JSON."""
    clean = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    clean = clean.replace("```json", "").replace("```", "").strip()
    return clean


def _parse_response(raw: str, slide_index: int) -> SemanticSlide:
    """
    Парсит JSON-ответ LLM → SemanticSlide.
    Ожидаемый формат: {"blocks": [...], "total_lines": int}
    """
    clean = _strip_thinking(raw)
    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(f"Слайд {slide_index}: JSON не распознан: {e}\nRaw: {clean[:300]}")
        raise

    blocks_raw: list[dict] = data.get("blocks", [])
    blocks: list[SemanticBlock] = []

    for i, b in enumerate(blocks_raw):
        try:
            b_norm = normalize_for_model(b, SemanticBlock)
            # Гарантируем block_id если LLM пропустил
            if not b_norm.get("block_id"):
                b_norm["block_id"] = f"sb{i}"
            blocks.append(SemanticBlock(**b_norm))
        except Exception as e:
            logger.warning(f"Слайд {slide_index}, блок {i} пропущен: {e}")

    total_lines: int = data.get("total_lines") or sum(b.line_budget for b in blocks)

    return SemanticSlide(
        slide_index=slide_index,
        blocks=blocks,
        total_lines=total_lines,
    )


def analyze_slide(
    parsed_slide: dict,
    strategy: PresentationStrategy,
    slide_index: int,
    image_path: str | None = None,
) -> SemanticSlide:
    """
    Слой 0: анализирует один слайд и возвращает SemanticSlide.

    Args:
        parsed_slide:  dict (ParsedSlide.model_dump())
        strategy:      стратегия презентации
        slide_index:   индекс слайда
        image_path:    путь к JPG-скриншоту (опционально, для Vision)

    Returns:
        SemanticSlide с list[SemanticBlock]
    """
    logger.info(f"SemanticEditor: слайд {slide_index}, vision={image_path is not None}")

    system_prompt = _load_system_prompt()
    user_msg = _build_user_message(parsed_slide, strategy, slide_index)

    try:
        raw = call_llm(
            prompt=user_msg,
            model_name=MODEL_BRAIN,
            image_path=image_path,
            json_mode=False,   # False — ответ содержит <thinking>, потом JSON
            system_instruction=system_prompt,
        )
    except Exception as e:
        logger.error(f"Слайд {slide_index}: LLM вызов упал: {e}")
        raise

    result = _parse_response(raw, slide_index)
    logger.info(
        f"SemanticEditor слайд {slide_index}: "
        f"{len(result.blocks)} блоков, {result.total_lines} строк"
    )
    return result