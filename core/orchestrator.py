"""
Orchestrator v5 — главный пайплайн PPTX-AI.

Parser → Strategy → Semantic Editor → Prompt Assembler →
Spatial Architect → Enrich → LayoutEngine → SVG Renderer.

Ключевое: после Spatial Architect orchestrator обогащает GridBlock-и
данными из SemanticSlide (content, semantic_type, visual_subtype).
LLM не гоняет контент туда-сюда — только решает layout.
"""

import json
import logging
import sys
import time
from pathlib import Path
from postprocess.validator import validate, dump_chosen, ValidationResult

from core.config import TEMP_DIR
from core.config import TEMP_DIR, MAX_VALIDATOR_RETRIES
from models.contracts import (
    LayoutPlanV5,
    GridBlock,
    SemanticSlide,
    SemanticBlock,
    SlideGeometry,
    DesignedSlide,
    PresentationStrategy,
)

logger = logging.getLogger(__name__)

CACHE_DIR: Path = TEMP_DIR / "cache"


# ═══════════════════════════════════════════════════════════════
#  КЭШИРОВАНИЕ
# ═══════════════════════════════════════════════════════════════

def _cache_path(slide_idx: int | None, stage: str, ext: str = "json") -> Path:
    """Путь к файлу кэша для конкретного слайда и стадии."""
    if slide_idx is None:
        return CACHE_DIR / f"{stage}.{ext}"
    return CACHE_DIR / f"slide_{slide_idx}_{stage}.{ext}"


def _load_cache(slide_idx: int | None, stage: str, model_class=None):
    """Загружает кэш. Возвращает None если файла нет или он повреждён."""
    path = _cache_path(slide_idx, stage)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return model_class(**data) if model_class else data
    except Exception as e:
        logger.warning(f"Кэш повреждён {path}: {e}")
        return None


def _save_cache(
    slide_idx: int | None, stage: str, data, ext: str = "json"
) -> None:
    """Сохраняет данные в кэш."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(slide_idx, stage, ext)
    if hasattr(data, "model_dump_json"):
        path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
    elif isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def clear_cache() -> None:
    """Удаляет все файлы кэша."""
    if CACHE_DIR.exists():
        for f in CACHE_DIR.iterdir():
            f.unlink()
        logger.info("Кэш очищен")


# ═══════════════════════════════════════════════════════════════
#  ОБОГАЩЕНИЕ LAYOUT (Python, без LLM)
# ═══════════════════════════════════════════════════════════════

def _enrich_layout(
    layout: LayoutPlanV5,
    semantic: SemanticSlide,
) -> LayoutPlanV5:
    """
    Копирует content, semantic_type, visual_subtype из SemanticSlide
    в каждый GridBlock по совпадению block_id.

    Спейсеры (block_id начинается с 'spacer_') пропускаются — это
    декоративные блоки от Architect для дополнения col_span до 12.

    LLM не возвращает контент — только layout (row_start_cell, col_start,
    col_span, height_cells, render). Контент подставляет Python.
    """
    sem_index: dict[str, SemanticBlock] = {
        b.block_id: b for b in semantic.blocks
    }

    enriched_count = 0
    spacer_count = 0
    for row in layout.rows:
        for block in row.blocks:
            if block.block_id.startswith("spacer_"):
                block.semantic_type = "text"
                block.content = {}
                block.visual_subtype = None
                spacer_count += 1
                continue

            sem = sem_index.get(block.block_id)
            if sem is None:
                logger.warning(
                    f"Слайд {layout.slide_index}: block_id='{block.block_id}' "
                    f"не найден в SemanticSlide — пропускаем обогащение"
                )
                continue

            block.semantic_type = sem.semantic_type
            block.content = sem.content
            block.visual_subtype = sem.visual_subtype
            enriched_count += 1

    logger.info(
        f"Слайд {layout.slide_index}: обогащено {enriched_count} блоков, "
        f"спейсеров {spacer_count}, всего семантических {len(sem_index)}"
    )
    return layout


# ═══════════════════════════════════════════════════════════════
#  ОДИН СЛАЙД — цепочка v5
# ═══════════════════════════════════════════════════════════════

def _design_with_retry(
    semantic: SemanticSlide,
    strategy: PresentationStrategy,
    design_context: str,
    slide_index: int,
) -> tuple[LayoutPlanV5, ValidationResult]:
    """
    Цикл Architect → Enrich → Validate с feedback.

    Делает до MAX_VALIDATOR_RETRIES + 1 попыток. Если ни одна не валидна,
    возвращает лучший вариант по минимальному penalty.
    Каждая попытка дампится через validator.

    Returns:
        (best_plan, best_result) — лучший план и его валидация.
    """
    from agents.spatial_architect import design_slide

    proposed_spans: dict[str, int] = {
        b.block_id: b.proposed_col_span for b in semantic.blocks
    }

    attempts: list[tuple[LayoutPlanV5, ValidationResult]] = []
    feedback: str | None = None
    max_attempts = MAX_VALIDATOR_RETRIES + 1

    for attempt in range(max_attempts):
        try:
            plan = design_slide(
                semantic_slide=semantic,
                strategy=strategy,
                design_context=design_context,
                slide_index=slide_index,
                feedback=feedback,
            )
        except Exception as e:
            logger.error(
                f"Слайд {slide_index} попытка {attempt}: Architect упал: {e}"
            )
            if attempts:
                break
            raise

        plan = _enrich_layout(plan, semantic)
        result = validate(
            plan=plan,
            slide_index=slide_index,
            attempt=attempt,
            proposed_spans=proposed_spans,
        )
        attempts.append((plan, result))

        if result.is_valid:
            logger.info(
                f"Слайд {slide_index}: валидный план с попытки {attempt}"
            )
            break

        if result.changed_col_spans:
            logger.warning(
                f"Слайд {slide_index} попытка {attempt}: Architect изменил "
                f"col_span у {list(result.changed_col_spans.keys())} — "
                f"height_cells может быть неточным "
                f"(пере-измерение через tool в Фазе 4.9.2)"
            )

        feedback = result.feedback
        logger.info(
            f"Слайд {slide_index}: попытка {attempt} невалидна "
            f"(penalty={result.penalty}), retry..."
        )

    best_plan, best_result = min(attempts, key=lambda pr: pr[1].penalty)
    if not best_result.is_valid:
        logger.warning(
            f"Слайд {slide_index}: все {len(attempts)} попыток невалидны, "
            f"выбран лучший penalty={best_result.penalty}"
        )

    dump_chosen(best_plan, best_result, slide_index)
    return best_plan, best_result


def _process_slide(
    slide_index: int,
    parsed_slide: dict,
    strategy: PresentationStrategy,
    image_path: str | None,
    use_cache: bool,
) -> DesignedSlide:
    """Слой 0 → 0.5 → 1 → Enrich → LayoutEngine → SVG для одного слайда."""
    from agents.semantic_editor import analyze_slide
    from agents.spatial_architect import design_slide
    from core.prompt_assembler import assemble_prompt_context
    from core.layout_engine import compute_geometry
    from core.svg_renderer import render_slide

    # ── Слой 0: Semantic Editor ─────────────────────────────────
    semantic: SemanticSlide | None = (
        _load_cache(slide_index, "semantic", SemanticSlide) if use_cache else None
    )
    if semantic:
        logger.info(f"[CACHE] Semantic слайда {slide_index}")
    else:
        semantic = analyze_slide(
            parsed_slide=parsed_slide,
            strategy=strategy,
            slide_index=slide_index,
            image_path=image_path,
        )
        _save_cache(slide_index, "semantic", semantic)

    logger.info(
        f"Слайд {slide_index}: {len(semantic.blocks)} блоков, "
        f"{semantic.total_height_cells} клеток"
    )

    # ── Слой 0.5: Prompt Assembler ──────────────────────────────
    recommended = [b.semantic_type for b in semantic.blocks]
    for block in semantic.blocks:
        if block.visual_subtype and block.visual_subtype not in recommended:
            recommended.append(block.visual_subtype)

    design_context = assemble_prompt_context(
        recommended_modules=recommended,
        strategy=strategy,
    )

    # ── Слой 1: Spatial Architect → Enrich → Validator (retry) ──
    layout: LayoutPlanV5 | None = (
        _load_cache(slide_index, "layout", LayoutPlanV5) if use_cache else None
    )
    if layout:
        logger.info(f"[CACHE] Layout слайда {slide_index}")
    else:
        layout, val_result = _design_with_retry(
            semantic=semantic,
            strategy=strategy,
            design_context=design_context,
            slide_index=slide_index,
        )
        if val_result.is_valid:
            _save_cache(slide_index, "layout", layout)
        else:
            logger.info(
                f"Слайд {slide_index}: невалидный план не кэшируется"
            )

    logger.info(
        f"Слайд {slide_index}: {len(layout.rows)} рядов, "
        f"role={layout.slide_role}"
    )

    # ── Обогащение: Python подставляет content в GridBlock ──────
    layout = _enrich_layout(layout, semantic)

    # ── LayoutEngine → пиксели ──────────────────────────────────
    geo: SlideGeometry = compute_geometry(layout, strategy)
    _save_cache(slide_index, "geometry", geo)

    # ── SVG Renderer ────────────────────────────────────────────
    if use_cache:
        svg_path = _cache_path(slide_index, "svg", "svg")
        if svg_path.exists():
            logger.info(f"[CACHE] SVG слайда {slide_index}")
            return DesignedSlide(
                slide_index=slide_index,
                svg_code=svg_path.read_text(encoding="utf-8"),
            )

    designed = render_slide(geo)
    _save_cache(slide_index, "svg", designed.svg_code, ext="svg")
    return designed


# ═══════════════════════════════════════════════════════════════
#  ПАЙПЛАЙН v5
# ═══════════════════════════════════════════════════════════════

def run_pipeline(
    pptx_path: str,
    accent_color: str | None = None,
    use_cache: bool = True,
    slides: list[int] | None = None,
    use_vision: bool = True,
) -> list[DesignedSlide]:
    """
    Полный пайплайн v5:
      Parser → Strategy → Semantic Editor → Prompt Assembler →
      Spatial Architect → Enrich → LayoutEngine → SVG Renderer.

    Args:
        pptx_path:    путь к PPTX файлу.
        accent_color: ручной цвет (перебивает Strategy).
        use_cache:    читать/писать кэш.
        slides:       список индексов (None = все).
        use_vision:   передавать изображение в Semantic Editor.
    """
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich
    from agents.strategy_director import build_strategy

    t_start = time.time()
    logger.info("=" * 60)
    logger.info(f"PIPELINE v5 START: {pptx_path}")
    logger.info(f"vision={use_vision}, cache={use_cache}")
    logger.info("=" * 60)

    if not use_cache:
        clear_cache()

    # ── ШАГ 1: Рендеринг PPTX → JPG ────────────────────────────
    logger.info("ШАГ 1: Рендеринг PPTX → JPG")
    images = render_slides(pptx_path)

    # ── ШАГ 2: Парсинг PPTX ────────────────────────────────────
    logger.info("ШАГ 2: Парсинг PPTX")
    parsed_pres = parse_pptx_rich(pptx_path)

    if not images or not parsed_pres:
        logger.error("Нет данных из презентации!")
        return []

    parsed_list = [s.model_dump() for s in parsed_pres.slides]

    # ── ШАГ 3: Strategy Director ────────────────────────────────
    logger.info("ШАГ 3: Strategy Director")
    strategy: PresentationStrategy | None = (
        _load_cache(None, "strategy", PresentationStrategy) if use_cache else None
    )
    if strategy:
        logger.info("[CACHE] Strategy загружена")
    else:
        strategy = build_strategy([str(img) for img in images], parsed_list)
        _save_cache(None, "strategy", strategy)

    if accent_color:
        logger.info(f"Accent override: {accent_color}")
        strategy.accent_color = accent_color

    logger.info(
        f"Strategy: header={strategy.header_type}, style={strategy.style_mode}, "
        f"mode={strategy.presentation_mode}, accent={strategy.accent_color}"
    )

    # ── Фильтр слайдов ──────────────────────────────────────────
    total = min(len(images), len(parsed_list))
    indices = (
        [i for i in slides if i < total] if slides else list(range(total))
    )
    logger.info(f"Слайдов к обработке: {len(indices)} из {total}")

    # ── ШАГ 4-6: Обработка каждого слайда ───────────────────────
    results: list[DesignedSlide] = []
    for idx in indices:
        t_slide = time.time()
        try:
            designed = _process_slide(
                slide_index=idx,
                parsed_slide=parsed_list[idx],
                strategy=strategy,
                image_path=str(images[idx]) if use_vision else None,
                use_cache=use_cache,
            )
            results.append(designed)
            logger.info(f"Слайд {idx} готов за {time.time() - t_slide:.1f}с")
        except Exception as e:
            logger.error(f"Слайд {idx} упал: {e}", exc_info=True)
            results.append(DesignedSlide(slide_index=idx, svg_code=""))

    logger.info("=" * 60)
    logger.info(
        f"PIPELINE v5 DONE: {len(results)} слайдов "
        f"за {time.time() - t_start:.1f}с"
    )
    logger.info("=" * 60)
    return results


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    pptx_path = (
        sys.argv[1] if len(sys.argv) > 1
        else "projects/test_map/test_maps.pptx"
    )
    no_cache = "--no-cache" in sys.argv
    no_vision = "--no-vision" in sys.argv

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
    )

    for r in results:
        status = "OK" if len(r.svg_code) > 100 else "FAIL"
        logger.info(
            f"Слайд {r.slide_index}: {status} ({len(r.svg_code)} символов)"
        )