"""Orchestrator v2 — полный пайплайн с батчингом и async."""

import json
import logging
import sys
import time
from pathlib import Path

from core.config import TEMP_DIR, COLOR_ACCENT_DEFAULT
from models.contracts import SlideClassificationV2, LayoutPlan, DesignedSlide

logger = logging.getLogger(__name__)

CACHE_DIR = TEMP_DIR / "cache"


# === КЭШИРОВАНИЕ ===

def _cache_path(slide_idx: int, stage: str, ext: str = "json") -> Path:
    return CACHE_DIR / f"slide_{slide_idx}_{stage}.{ext}"


def _load_cache(slide_idx: int, stage: str, model_class=None):
    path = _cache_path(slide_idx, stage)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if model_class:
            return model_class(**data)
        return data
    except Exception as e:
        logger.warning(f"Кэш повреждён {path}: {e}")
        return None


def _save_cache(slide_idx: int, stage: str, data, ext: str = "json"):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(slide_idx, stage, ext)
    if hasattr(data, "model_dump_json"):
        path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
    elif isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_cache():
    if CACHE_DIR.exists():
        for f in CACHE_DIR.iterdir():
            f.unlink()
        logger.info("Кэш очищен")


# === ПАЙПЛАЙН ===

def run_pipeline(
    pptx_path: str,
    accent_color: str = COLOR_ACCENT_DEFAULT,
    use_cache: bool = True,
    slides: list[int] | None = None,
    use_vision: bool = True,
    use_batch: bool = True
):
    """
    Полный пайплайн: Parser → Classifier → Senior → Junior.

    Args:
        pptx_path: путь к PPTX
        accent_color: акцентный цвет
        use_cache: читать/писать кэш
        slides: список индексов (None = все)
        use_vision: True = поштучно с картинкой, False = батч без картинок
        use_batch: True = батч Senior, False = поштучно
    """
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich
    from agents.classifier import classify_slide_v2, classify_batch_v2
    from agents.senior_designer import design_slide_senior, design_batch_senior
    from agents.junior_designer import design_slide_junior, design_all_junior

    start_time = time.time()
    logger.info(f"{'='*60}")
    logger.info(f"PIPELINE START: {pptx_path}")
    logger.info(f"vision={use_vision}, batch={use_batch}, cache={use_cache}")
    logger.info(f"{'='*60}")

    if not use_cache:
        clear_cache()

    # ШАГ 1: Рендеринг
    logger.info("ШАГ 1: Рендеринг")
    images = render_slides(pptx_path)

    # ШАГ 2: Парсинг
    logger.info("ШАГ 2: Парсинг")
    parsed_pres = parse_pptx_rich(pptx_path)

    if not images or not parsed_pres:
        logger.error("Нет данных из презентации!")
        return []

    # parsed может быть Pydantic объектом или списком
    if hasattr(parsed_pres, 'slides'):
        parsed_list = [s.model_dump() for s in parsed_pres.slides]
    else:
        parsed_list = parsed_pres

    # Фильтр слайдов
    total = min(len(images), len(parsed_list))
    if slides is not None:
        indices = [i for i in slides if i < total]
    else:
        indices = list(range(total))

    logger.info(f"Слайдов к обработке: {len(indices)} из {total}")

    sel_images = [images[i] for i in indices]
    sel_parsed = [parsed_list[i] for i in indices]

    # ШАГ 3: Классификация
    logger.info(f"ШАГ 3: Классификация ({len(indices)} слайдов)")

    classifications = []
    uncached_indices = []
    uncached_images = []
    uncached_parsed = []

    for i, idx in enumerate(indices):
        cached = _load_cache(idx, "classification", SlideClassificationV2) if use_cache else None
        if cached:
            logger.info(f"[CACHE] Классификация слайда {idx}")
            classifications.append(cached)
        else:
            classifications.append(None)  # заглушка
            uncached_indices.append(i)
            uncached_images.append(sel_images[i])
            uncached_parsed.append(sel_parsed[i])

    if uncached_indices:
        logger.info(f"Классифицируем {len(uncached_indices)} слайдов (не в кэше)")

        if use_vision:
            # Поштучно с картинками
            for j, (img, parsed) in enumerate(zip(uncached_images, uncached_parsed)):
                real_idx = indices[uncached_indices[j]]
                result = classify_slide_v2(img, parsed, slide_index=real_idx)
                classifications[uncached_indices[j]] = result
                _save_cache(real_idx, "classification", result)
        else:
            # Батчем без картинок
            batch_results = classify_batch_v2(uncached_images, uncached_parsed)
            for j, result in enumerate(batch_results):
                real_idx = indices[uncached_indices[j]]
                result.slide_index = real_idx
                classifications[uncached_indices[j]] = result
                _save_cache(real_idx, "classification", result)

    cls_time = time.time() - start_time
    logger.info(f"Классификация завершена за {cls_time:.1f}с")

    # ШАГ 4: Senior Designer
    logger.info(f"ШАГ 4: Senior Designer ({len(indices)} слайдов)")

    layout_plans = []
    uncached_cls = []
    uncached_parsed_sr = []
    uncached_sr_indices = []

    for i, idx in enumerate(indices):
        cached = _load_cache(idx, "layout_plan", LayoutPlan) if use_cache else None
        if cached:
            logger.info(f"[CACHE] LayoutPlan слайда {idx}")
            layout_plans.append(cached)
        else:
            layout_plans.append(None)
            uncached_sr_indices.append(i)
            uncached_cls.append(classifications[i])
            uncached_parsed_sr.append(sel_parsed[i])

    if uncached_sr_indices:
        logger.info(f"Senior Designer для {len(uncached_sr_indices)} слайдов")

        if use_batch and len(uncached_cls) > 1:
            batch_results = design_batch_senior(uncached_cls, uncached_parsed_sr, accent_color)
            for j, result in enumerate(batch_results):
                real_idx = indices[uncached_sr_indices[j]]
                result.slide_index = real_idx
                layout_plans[uncached_sr_indices[j]] = result
                _save_cache(real_idx, "layout_plan", result)
        else:
            for j, (cls, parsed) in enumerate(zip(uncached_cls, uncached_parsed_sr)):
                result = design_slide_senior(cls, parsed, accent_color)
                layout_plans[uncached_sr_indices[j]] = result
                real_idx = indices[uncached_sr_indices[j]]
                _save_cache(real_idx, "layout_plan", result)

    sr_time = time.time() - start_time - cls_time
    logger.info(f"Senior Designer завершён за {sr_time:.1f}с")

    # ШАГ 5: Junior Designer (async параллельно)
    logger.info(f"ШАГ 5: Junior Designer ({len(indices)} слайдов, async)")

    uncached_plans = []
    uncached_jr_cls = []
    uncached_jr_indices = []
    cached_results = {}

    for i, idx in enumerate(indices):
        if use_cache:
            svg_path = _cache_path(idx, "svg", "svg")
            if svg_path.exists():
                logger.info(f"[CACHE] SVG слайда {idx}")
                svg_code = svg_path.read_text(encoding="utf-8")
                cached_results[i] = DesignedSlide(slide_index=idx, svg_code=svg_code)
                continue

        uncached_jr_indices.append(i)
        uncached_plans.append(layout_plans[i])
        uncached_jr_cls.append(classifications[i])

    if uncached_jr_indices:
        logger.info(f"Junior async для {len(uncached_jr_indices)} слайдов")
        junior_results = design_all_junior(uncached_plans, uncached_jr_cls, accent_color)

        for j, result in enumerate(junior_results):
            real_idx = indices[uncached_jr_indices[j]]
            result.slide_index = real_idx
            _save_cache(real_idx, "svg", result.svg_code, ext="svg")
            cached_results[uncached_jr_indices[j]] = result

    # Собираем в правильном порядке
    results = [cached_results[i] for i in range(len(indices))]

    total_time = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"PIPELINE DONE: {len(results)} слайдов за {total_time:.1f}с")
    logger.info(f"  Classifier: {cls_time:.1f}с")
    logger.info(f"  Senior: {sr_time:.1f}с")
    logger.info(f"  Junior: {total_time - cls_time - sr_time:.1f}с")
    logger.info(f"{'='*60}")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"

    # Парсим аргументы
    no_cache = "--no-cache" in sys.argv
    no_vision = "--no-vision" in sys.argv
    no_batch = "--no-batch" in sys.argv

    slide_list = None
    for arg in sys.argv:
        if arg.startswith("--slides="):
            slide_list = [int(x) for x in arg.split("=")[1].split(",")]

    results = run_pipeline(
        pptx_path=pptx_path,
        use_cache=not no_cache,
        slides=slide_list,
        use_vision=not no_vision,
        use_batch=not no_batch
    )

    print(f"\n{'='*50}")
    print(f"ИТОГО: {len(results)} слайдов")
    for r in results:
        status = "OK" if len(r.svg_code) > 100 else "FAIL"
        print(f"  Слайд {r.slide_index}: {status} ({len(r.svg_code)} символов)")