"""Orchestrator v4 — Parser → Strategy → Architect → LayoutEngine → SVG Renderer."""

import json
import logging
import sys
import time
from pathlib import Path

from core.config import TEMP_DIR
from models.contracts import (
    LayoutPlan,
    SlideGeometry,
    DesignedSlide,
    PresentationStrategy,
)

logger = logging.getLogger(__name__)

CACHE_DIR = TEMP_DIR / "cache"


# ═══════════════════════════════════════════════════════════════
#  КЭШИРОВАНИЕ
# ═══════════════════════════════════════════════════════════════

def _cache_path(slide_idx: int | None, stage: str, ext: str = "json") -> Path:
    if slide_idx is None:
        return CACHE_DIR / f"{stage}.{ext}"
    return CACHE_DIR / f"slide_{slide_idx}_{stage}.{ext}"


def _load_cache(slide_idx: int | None, stage: str, model_class=None):
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


def _save_cache(slide_idx: int | None, stage: str, data, ext: str = "json"):
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


# ═══════════════════════════════════════════════════════════════
#  ПАЙПЛАЙН v4
# ═══════════════════════════════════════════════════════════════

def run_pipeline(
    pptx_path: str,
    accent_color: str | None = None,
    use_cache: bool = True,
    slides: list[int] | None = None,
    use_vision: bool = True,
    use_batch: bool = True,
):
    """
    Полный пайплайн v4:
      Parser → Strategy Director → Architect → LayoutEngine → SVG Renderer.

    Args:
        pptx_path: путь к PPTX файлу
        accent_color: ручной цвет (перебивает Strategy)
        use_cache: читать/писать кэш
        slides: список индексов слайдов (None = все)
        use_vision: поштучно с картинкой (True) / батч без картинок (False)
        use_batch: батч Architect (True) / поштучно (False)
    """
    # Ленивые импорты — чтобы не ломалось при import orchestrator
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich
    from agents.strategy_director import build_strategy
    from agents.architect import design_all
    from core.layout_engine import compute_geometry
    from core.svg_renderer import render_slide

    start_time = time.time()
    logger.info(f"{'='*60}")
    logger.info(f"PIPELINE v4 START: {pptx_path}")
    logger.info(f"vision={use_vision}, batch={use_batch}, cache={use_cache}")
    logger.info(f"{'='*60}")

    if not use_cache:
        clear_cache()

    # ── ШАГ 1: Рендеринг слайдов в JPG ─────────────────────────
    logger.info("ШАГ 1: Рендеринг PPTX → JPG")
    images = render_slides(pptx_path)

    # ── ШАГ 2: Парсинг PPTX ────────────────────────────────────
    logger.info("ШАГ 2: Парсинг PPTX")
    parsed_pres = parse_pptx_rich(pptx_path)

    if not images or not parsed_pres:
        logger.error("Нет данных из презентации!")
        return []

    parsed_list = [s.model_dump() for s in parsed_pres.slides]

    # ── ШАГ 3: Strategy Director (1 вызов на всю презу) ────────
    logger.info("ШАГ 3: Strategy Director")
    t3 = time.time()

    strategy: PresentationStrategy | None = (
        _load_cache(None, "strategy", PresentationStrategy) if use_cache else None
    )
    if strategy:
        logger.info("[CACHE] Strategy загружена")
    else:
        strategy = build_strategy(
            [str(img) for img in images],
            parsed_list,
        )
        _save_cache(None, "strategy", strategy)

    # Ручной accent перебивает
    if accent_color:
        logger.info(f"accent вручную: {accent_color} (было {strategy.accent_color})")
        strategy.accent_color = accent_color

    logger.info(
        f"Strategy: header={strategy.header_type}, style={strategy.style_mode}, "
        f"mode={strategy.presentation_mode}, accent={strategy.accent_color}, "
        f"rewrite={strategy.allow_rewrite}"
    )
    time_strategy = time.time() - t3

    # ── Фильтр слайдов ─────────────────────────────────────────
    total = min(len(images), len(parsed_list))
    if slides is not None:
        indices = [i for i in slides if i < total]
    else:
        indices = list(range(total))

    logger.info(f"Слайдов к обработке: {len(indices)} из {total}")

    sel_images = [str(images[i]) for i in indices]
    sel_parsed = [parsed_list[i] for i in indices]

    # ── ШАГ 4: Architect (классификация + layout plan) ──────────
    logger.info(f"ШАГ 4: Architect ({len(indices)} слайдов)")
    t4 = time.time()

    layout_plans: list[LayoutPlan] = []
    need_architect_idx = []  # позиция в sel_*
    need_architect_images = []
    need_architect_parsed = []
    need_architect_slides = []  # реальный slide_index

    for pos, idx in enumerate(indices):
        cached = (
            _load_cache(idx, "layout_plan", LayoutPlan) if use_cache else None
        )
        if cached:
            logger.info(f"[CACHE] LayoutPlan слайда {idx}")
            layout_plans.append(cached)
        else:
            layout_plans.append(None)  # placeholder
            need_architect_idx.append(pos)
            need_architect_images.append(sel_images[pos])
            need_architect_parsed.append(sel_parsed[pos])
            need_architect_slides.append(idx)

    if need_architect_idx:
        logger.info(f"Architect для {len(need_architect_idx)} слайдов")

        architect_results = design_all(
            images=need_architect_images,
            parsed_slides=need_architect_parsed,
            strategy=strategy,
            slide_indices=need_architect_slides,
            use_vision=use_vision,
            use_batch=use_batch,
        )

        for j, plan in enumerate(architect_results):
            pos = need_architect_idx[j]
            layout_plans[pos] = plan
            _save_cache(plan.slide_index, "layout_plan", plan)

    time_architect = time.time() - t4
    logger.info(f"Architect завершён за {time_architect:.1f}с")

    # ── ШАГ 5: LayoutEngine (grid → пиксели) ───────────────────
    logger.info(f"ШАГ 5: LayoutEngine ({len(indices)} слайдов)")
    t5 = time.time()

    geometries: list[SlideGeometry] = []
    for plan in layout_plans:
        geo = compute_geometry(plan, strategy)
        geometries.append(geo)
        _save_cache(plan.slide_index, "geometry", geo)

    time_layout = time.time() - t5
    logger.info(f"LayoutEngine завершён за {time_layout:.1f}с")

    # ── ШАГ 6: SVG Renderer (пиксели → SVG) ────────────────────
    logger.info(f"ШАГ 6: SVG Renderer ({len(indices)} слайдов)")
    t6 = time.time()

    results: list[DesignedSlide] = []
    for geo in geometries:
        # Проверяем кэш SVG
        if use_cache:
            svg_path = _cache_path(geo.slide_index, "svg", "svg")
            if svg_path.exists():
                logger.info(f"[CACHE] SVG слайда {geo.slide_index}")
                svg_code = svg_path.read_text(encoding="utf-8")
                results.append(DesignedSlide(
                    slide_index=geo.slide_index, svg_code=svg_code
                ))
                continue

        designed = render_slide(geo)
        _save_cache(geo.slide_index, "svg", designed.svg_code, ext="svg")
        results.append(designed)

    time_svg = time.time() - t6
    logger.info(f"SVG Renderer завершён за {time_svg:.1f}с")

    # ── ИТОГО ───────────────────────────────────────────────────
    total_time = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"PIPELINE v4 DONE: {len(results)} слайдов за {total_time:.1f}с")
    logger.info(f"  Strategy:    {time_strategy:.1f}с")
    logger.info(f"  Architect:   {time_architect:.1f}с")
    logger.info(f"  LayoutEngine:{time_layout:.1f}с")
    logger.info(f"  SVG Renderer:{time_svg:.1f}с")
    logger.info(f"{'='*60}")

    return results


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    pptx_path = (
        sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    )

    no_cache = "--no-cache" in sys.argv
    no_vision = "--no-vision" in sys.argv
    no_batch = "--no-batch" in sys.argv

    accent_override = None
    slide_list = None
    for arg in sys.argv:
        if arg.startswith("--slides="):
            slide_list = [int(x) for x in arg.split("=")[1].split(",")]
        if arg.startswith("--accent="):
            accent_override = arg.split("=")[1]

    results = run_pipeline(
        pptx_path=pptx_path,
        accent_color=accent_override,
        use_cache=not no_cache,
        slides=slide_list,
        use_vision=not no_vision,
        use_batch=not no_batch,
    )

    print(f"\n{'='*50}")
    print(f"ИТОГО: {len(results)} слайдов")
    for r in results:
        status = "OK" if len(r.svg_code) > 100 else "FAIL"
        print(f"  Слайд {r.slide_index}: {status} ({len(r.svg_code)} символов)")