"""Агент для классификации слайдов — поштучно или батчем до 20."""

import json
import logging
import sys
from pathlib import Path

from core.llm_client import call_llm
from core.config import MODEL_CLASSIFIER, CONFIG_DIR
from core.llm_normalize import normalize_for_model
from models.contracts import SlideClassificationV2

logger = logging.getLogger(__name__)

BATCH_LIMIT = 20


def _load_system_prompt() -> str:
    """Загружает системный промпт: classifier.md + §1 из core_rules."""
    classifier_path = CONFIG_DIR / "classifier.md"
    prompt = classifier_path.read_text(encoding="utf-8")

    rules_path = CONFIG_DIR / "core_rules.md"
    if rules_path.exists():
        content = rules_path.read_text(encoding="utf-8")
        start = content.find("## 1.")
        end = content.find("## 2.")
        if start != -1 and end != -1:
            prompt += "\n\n# CORE RULES §1\n" + content[start:end]

    return prompt


def classify_slide_v2(
    image_path: str,
    parsed_slide: dict,
    slide_index: int,
    user_header_pref: str = "auto"
) -> SlideClassificationV2:
    """Классификация одного слайда (с картинкой)."""
    logger.info(f"Классификация слайда {slide_index}")

    system_prompt = _load_system_prompt()
    parsed_str = json.dumps(parsed_slide, ensure_ascii=False, indent=2)
    user_msg = f"# SLIDE {slide_index}\n# PARSED DATA\n{parsed_str}\n\n# USER HEADER PREFERENCE\n{user_header_pref}"

    raw = call_llm(
        prompt=user_msg,
        model_name=MODEL_CLASSIFIER,
        image_path=image_path,
        json_mode=True,
        system_instruction=system_prompt
    )

    data = json.loads(raw.replace("```json", "").replace("```", "").strip())
    data.pop("slide_index", None)
    data = normalize_for_model(data, SlideClassificationV2)
    result = SlideClassificationV2(slide_index=slide_index, **data)

    logger.info(f"Слайд {slide_index}: role={result.slide_role}, objects={result.objects}")
    return result


def classify_batch_v2(
    image_paths: list[str],
    parsed_slides: list[dict],
    user_header_pref: str = "auto"
) -> list[SlideClassificationV2]:
    """Батч-классификация: без картинок, только parsed данные. До 20 слайдов за вызов."""
    logger.info(f"Батч-классификация: {len(parsed_slides)} слайдов")

    system_prompt = _load_system_prompt()
    results = []

    for batch_start in range(0, len(parsed_slides), BATCH_LIMIT):
        batch_end = min(batch_start + BATCH_LIMIT, len(parsed_slides))
        batch = parsed_slides[batch_start:batch_end]

        logger.info(f"Батч [{batch_start}:{batch_end}] — {len(batch)} слайдов")

        slides_data = []
        for i, parsed in enumerate(batch):
            idx = batch_start + i
            slides_data.append({"slide_index": idx, "parsed": parsed})

        user_msg = (
            f"Classify ALL slides below. Return a JSON array of objects.\n"
            f"Each object must match SlideClassificationV2 schema.\n"
            f"USER HEADER PREFERENCE: {user_header_pref}\n\n"
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

        # Gemini может вернуть {slides: [...]} или просто [...]
        if isinstance(arr, dict):
            arr = arr.get("slides", arr.get("results", list(arr.values())[0]))

        for item in arr:
            idx = item.pop("slide_index", batch_start + len(results))
            item = normalize_for_model(item, SlideClassificationV2)
            results.append(SlideClassificationV2(slide_index=idx, **item))

        logger.info(f"Батч готов, всего классифицировано: {len(results)}")

    return results


def classify_all_v2(
    image_paths: list[str],
    parsed_slides: list[dict],
    user_header_pref: str = "auto",
    use_vision: bool = True
) -> list[SlideClassificationV2]:
    """Умная классификация: vision поштучно или батч без картинок."""
    if use_vision:
        logger.info("Режим Vision: поштучная классификация с картинками")
        results = []
        for idx, (img, parsed) in enumerate(zip(image_paths, parsed_slides)):
            result = classify_slide_v2(img, parsed, idx, user_header_pref)
            results.append(result)
        return results
    else:
        return classify_batch_v2(image_paths, parsed_slides, user_header_pref)


if __name__ == "__main__":
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    logger.info(f"Тест классификации: {pptx_path}")

    images = render_slides(pptx_path)
    parsed = parse_pptx_rich(pptx_path)

    if not images or not parsed:
        logger.error("Нет данных")
        sys.exit(1)

    # Тест одного слайда с vision
    result = classify_slide_v2(images[0], parsed.slides[0].model_dump(), slide_index=0)
    print(f"\nVision: role={result.slide_role}, objects={result.objects}")

    # Тест батча без vision
    all_parsed = [s.model_dump() for s in parsed.slides]
    batch_results = classify_batch_v2(images, all_parsed)
    for r in batch_results:
        print(f"Batch slide {r.slide_index}: role={r.slide_role}, objects={r.objects}")