"""Агент Senior Designer v2 — планирование композиции, поштучно или батчем до 10."""

import json
import logging
import sys
from pathlib import Path

from core.llm_client import call_llm
from core.config import MODEL_BRAIN, PROMPTS_DIR
from core.llm_normalize import normalize_for_model
from core.prompt_assembler import assemble_prompt
from models.contracts import SlideClassificationV2, LayoutPlan

logger = logging.getLogger(__name__)

BATCH_LIMIT = 10


def _load_system_prompt(classification: SlideClassificationV2) -> str:
    """Загружает системный промпт: senior_designer.md + собранные rules."""
    prompt_path = PROMPTS_DIR / "senior_designer.md"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    design_rules = assemble_prompt(classification)
    return f"{prompt_template}\n\n# DESIGN RULES\n{design_rules}"


def design_slide_senior(
    classification: SlideClassificationV2,
    parsed_slide: dict,
    accent_color: str = "#0066CC"
) -> LayoutPlan:
    """Генерирует LayoutPlan для одного слайда."""
    idx = classification.slide_index
    logger.info(f"Senior Designer: слайд {idx}")

    system_prompt = _load_system_prompt(classification)

    user_msg = (
        f"# CLASSIFICATION\n{classification.model_dump_json(indent=2)}\n\n"
        f"# PARSED CONTENT\n{json.dumps(parsed_slide, ensure_ascii=False, indent=2)}\n\n"
        f"# ACCENT COLOR\n{accent_color}"
    )

    raw = call_llm(
        prompt=user_msg,
        model_name=MODEL_BRAIN,
        json_mode=True,
        system_instruction=system_prompt
    )

    data = json.loads(raw.replace("```json", "").replace("```", "").strip())
    data.pop("slide_index", None)
    data = normalize_for_model(data, LayoutPlan)
    result = LayoutPlan(slide_index=idx, **data)

    rows_count = len(result.rows) if result.rows else 0
    logger.info(f"Слайд {idx}: schema={result.composition_schema}, rows={rows_count}")
    return result


def design_batch_senior(
    classifications: list[SlideClassificationV2],
    parsed_slides: list[dict],
    accent_color: str = "#0066CC"
) -> list[LayoutPlan]:
    """Батч до 10 слайдов за вызов. Все слайды должны иметь одинаковый style_mode и header_type."""
    logger.info(f"Senior батч: {len(classifications)} слайдов")

    results = []

    for batch_start in range(0, len(classifications), BATCH_LIMIT):
        batch_end = min(batch_start + BATCH_LIMIT, len(classifications))
        batch_cls = classifications[batch_start:batch_end]
        batch_parsed = parsed_slides[batch_start:batch_end]

        logger.info(f"Батч [{batch_start}:{batch_end}] — {len(batch_cls)} слайдов")

        # System prompt берём от первого слайда в батче
        # (style + header rules одинаковые для всей презентации)
        system_prompt = _load_system_prompt(batch_cls[0])

        slides_data = []
        for cls, parsed in zip(batch_cls, batch_parsed):
            slides_data.append({
                "slide_index": cls.slide_index,
                "classification": json.loads(cls.model_dump_json()),
                "parsed_content": parsed
            })

        user_msg = (
            f"Create a LayoutPlan for EACH slide below.\n"
            f"Return a JSON array of LayoutPlan objects.\n"
            f"ACCENT COLOR: {accent_color}\n\n"
            f"# SLIDES\n{json.dumps(slides_data, ensure_ascii=False, indent=2)}"
        )

        raw = call_llm(
            prompt=user_msg,
            model_name=MODEL_BRAIN,
            json_mode=True,
            system_instruction=system_prompt
        )

        clean = raw.replace("```json", "").replace("```", "").strip()
        arr = json.loads(clean)

        if isinstance(arr, dict):
            arr = arr.get("slides", arr.get("results", arr.get("layout_plans", list(arr.values())[0])))

        for item in arr:
            idx = item.pop("slide_index", batch_start + len(results))
            item = normalize_for_model(item, LayoutPlan)
            results.append(LayoutPlan(slide_index=idx, **item))

        logger.info(f"Батч готов, всего планов: {len(results)}")

    return results


def design_all_senior(
    classifications: list[SlideClassificationV2],
    parsed_slides: list[dict],
    accent_color: str = "#0066CC",
    use_batch: bool = True
) -> list[LayoutPlan]:
    """Умный выбор: батч или поштучно."""
    if use_batch and len(classifications) > 1:
        return design_batch_senior(classifications, parsed_slides, accent_color)
    else:
        results = []
        for cls, parsed in zip(classifications, parsed_slides):
            result = design_slide_senior(cls, parsed, accent_color)
            results.append(result)
        return results


if __name__ == "__main__":
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich
    from agents.classifier import classify_slide_v2

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    logger.info(f"Тест Senior Designer: {pptx_path}")

    images = render_slides(pptx_path)
    parsed = parse_pptx_rich(pptx_path)

    if not images or not parsed:
        logger.error("Нет данных")
        sys.exit(1)

    classification = classify_slide_v2(images[0], parsed.slides[0].model_dump(), slide_index=0)
    layout_plan = design_slide_senior(classification, parsed.slides[0].model_dump())

    print(f"\nSchema: {layout_plan.composition_schema}")
    print(f"Rows: {len(layout_plan.rows)}")
    print(layout_plan.model_dump_json(indent=2))