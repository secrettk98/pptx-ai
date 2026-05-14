"""Strategy Director — формирует единую стратегию редизайна на уровне всей презентации."""

import json
import logging
import sys
from pathlib import Path

from core.llm.client import call_llm
from core.config import MODEL_CLASSIFIER, PROMPTS_DIR
from core.llm.normalize import normalize_for_model
from models.contracts import PresentationStrategy

logger = logging.getLogger(__name__)


def _load_system_prompt() -> str:
    """Загружает системный промпт Strategy Director."""
    try:
        path = PROMPTS_DIR / "strategy_director.md"
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Ошибка загрузки системного промпта Strategy Director: {e}")
        raise


def build_strategy(
    image_paths: list[str],
    parsed_slides: list[dict]
) -> PresentationStrategy:
    """Анализирует всю презентацию (картинки + parsed) и возвращает единую стратегию.

    Args:
        image_paths: пути к превью всех слайдов
        parsed_slides: список dict с parsed данными слайдов

    Returns:
        PresentationStrategy с header_type, style_mode, accent_color, presentation_mode, allow_rewrite
    """
    logger.info(f"Strategy Director: анализ {len(parsed_slides)} слайдов")

    system_prompt = _load_system_prompt()

    # Краткое описание каждого слайда для overview
    overview = []
    for i, parsed in enumerate(parsed_slides):
        texts = []
        for shape in parsed.get("shapes", []):
            texts.extend(shape.get("texts", []))
        overview.append({
            "slide_index": i,
            "shape_count": len(parsed.get("shapes", [])),
            "texts_preview": [t[:80] for t in texts[:5]]
        })

    user_msg = (
        f"Analyze ALL slides below and return ONE PresentationStrategy JSON object.\n\n"
        f"# PRESENTATION OVERVIEW\n{json.dumps(overview, ensure_ascii=False, indent=2)}"
    )

    try:
        # Передаём ВСЕ картинки одним вызовом (Gemini поддерживает мульти-изображения)
        raw = call_llm(
            prompt=user_msg,
            model_name=MODEL_CLASSIFIER,
            image_path=image_paths,
            json_mode=True,
            system_instruction=system_prompt
        )

        clean = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        data = normalize_for_model(data, PresentationStrategy)
        result = PresentationStrategy(**data)

        logger.info(
            f"Strategy: header={result.header_type}, style={result.style_mode}, "
            f"mode={result.presentation_mode}, accent={result.accent_color}, "
            f"rewrite={result.allow_rewrite}"
        )
        return result
    except Exception as e:
        logger.error(f"Ошибка при формировании стратегии презентации: {e}")
        raise


if __name__ == "__main__":
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    logger.info(f"Тест Strategy Director: {pptx_path}")

    try:
        images = render_slides(pptx_path)
        parsed = parse_pptx_rich(pptx_path)

        if not images or not parsed:
            logger.error("Нет данных для анализа")
            sys.exit(1)

        parsed_list = [s.model_dump() for s in parsed.slides]
        strategy = build_strategy([str(img) for img in images], parsed_list)

        print(f"\nStrategy: {strategy.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"Критическая ошибка в тесте Strategy Director: {e}")
        sys.exit(1)