"""Slide Architect — классификация + layout plan в одном шаге."""

import json
import logging
from pathlib import Path

from core.llm_client import call_llm
from core.config import MODEL_CLASSIFIER, PROMPTS_DIR
from core.llm_normalize import normalize_for_model
from core.prompt_assembler import assemble_rules
from models.contracts import PresentationStrategy, LayoutPlan

logger = logging.getLogger(__name__)

BATCH_LIMIT = 10


def _load_system_prompt(strategy: PresentationStrategy) -> str:
    """Загружает системный промпт: architect.md + design rules."""
    prompt_path = PROMPTS_DIR / "architect.md"
    template = prompt_path.read_text(encoding="utf-8")
    design_rules = assemble_rules(strategy)
    return f"{template}\n\n# DESIGN RULES\n{design_rules}"


def design_slide(
    image_path: str,
    parsed_slide: dict,
    strategy: PresentationStrategy,
    slide_index: int
) -> LayoutPlan:
    """Один слайд: image + parsed → LayoutPlan."""
    logger.info(f"Architect: слайд {slide_index}")

    system_prompt = _load_system_prompt(strategy)

    header_type = "A" if strategy.header_type == "fixed" else "B"

    user_msg = (
        f"# STRATEGY\n"
        f"header_type: {header_type}\n"
        f"style_mode: {strategy.style_mode}\n"
        f"accent_color: {strategy.accent_color}\n"
        f"presentation_mode: {strategy.presentation_mode}\n"
        f"allow_rewrite: {strategy.allow_rewrite}\n\n"
        f"# SLIDE INDEX\n{slide_index}\n\n"
        f"# PARSED CONTENT\n{json.dumps(parsed_slide, ensure_ascii=False, indent=2)}"
    )

    raw = call_llm(
        prompt=user_msg,
        model_name=MODEL_CLASSIFIER,
        image_path=image_path,
        json_mode=True,
        system_instruction=system_prompt
    )

    data = json.loads(raw.replace("```json", "").replace("```", "").strip())
    data.pop("slide_index", None)

    # Принудительно ставим strategy-значения
    data["header_type"] = header_type
    data["style_mode"] = strategy.style_mode

    data = normalize_for_model(data, LayoutPlan)
    result = LayoutPlan(slide_index=slide_index, **data)

    rows_count = len(result.rows) if result.rows else 0
    logger.info(f"Слайд {slide_index}: role={result.slide_role}, schema={result.composition_schema}, rows={rows_count}")
    return result


def design_batch(
    parsed_slides: list[dict],
    strategy: PresentationStrategy,
    slide_indices: list[int]
) -> list[LayoutPlan]:
    """Батч без vision — до 10 слайдов за вызов."""
    logger.info(f"Architect батч: {len(parsed_slides)} слайдов (без vision)")

    system_prompt = _load_system_prompt(strategy)
    header_type = "A" if strategy.header_type == "fixed" else "B"
    results = []

    for batch_start in range(0, len(parsed_slides), BATCH_LIMIT):
        batch_end = min(batch_start + BATCH_LIMIT, len(parsed_slides))
        batch_parsed = parsed_slides[batch_start:batch_end]
        batch_indices = slide_indices[batch_start:batch_end]

        logger.info(f"Батч [{batch_start}:{batch_end}] — {len(batch_parsed)} слайдов")

        slides_data = []
        for idx, parsed in zip(batch_indices, batch_parsed):
            slides_data.append({
                "slide_index": idx,
                "parsed_content": parsed
            })

        user_msg = (
            f"Create a LayoutPlan for EACH slide below.\n"
            f"Return a JSON array of LayoutPlan objects.\n\n"
            f"# STRATEGY\n"
            f"header_type: {header_type}\n"
            f"style_mode: {strategy.style_mode}\n"
            f"accent_color: {strategy.accent_color}\n"
            f"presentation_mode: {strategy.presentation_mode}\n"
            f"allow_rewrite: {strategy.allow_rewrite}\n\n"
            f"# SLIDES\n{json.dumps(slides_data, ensure_ascii=False, indent=2)}"
        )

        raw = call_llm(
            prompt=user_msg,
            model_name=MODEL_CLASSIFIER,
            json_mode=True,
            system_instruction=system_prompt
        )

        clean = raw.replace("```json", "").replace("```", "").strip()
        arr = json.loads(clean)

        if isinstance(arr, dict):
            arr = arr.get("slides", arr.get("results", arr.get("layout_plans", list(arr.values())[0])))

        for item in arr:
            idx = item.pop("slide_index", batch_start + len(results))
            item["header_type"] = header_type
            item["style_mode"] = strategy.style_mode
            item = normalize_for_model(item, LayoutPlan)
            results.append(LayoutPlan(slide_index=idx, **item))

        logger.info(f"Батч готов, всего планов: {len(results)}")

    return results


def design_all(
    images: list[str],
    parsed_slides: list[dict],
    strategy: PresentationStrategy,
    slide_indices: list[int],
    use_vision: bool = True,
    use_batch: bool = True
) -> list[LayoutPlan]:
    """Умный выбор: поштучно с vision или батч без vision."""
    if use_vision:
        # Поштучно с картинкой
        results = []
        for img, parsed, idx in zip(images, parsed_slides, slide_indices):
            result = design_slide(img, parsed, strategy, idx)
            results.append(result)
        return results
    else:
        # Батч без vision
        if use_batch and len(parsed_slides) > 1:
            return design_batch(parsed_slides, strategy, slide_indices)
        else:
            # Поштучно без vision (fallback)
            results = []
            for parsed, idx in zip(parsed_slides, slide_indices):
                result = design_slide("", parsed, strategy, idx)
                results.append(result)
            return results