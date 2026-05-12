"""Агент Junior Designer v2 — генерация SVG, async параллельно до 5 слайдов."""

import asyncio
import json
import logging
import sys
from pathlib import Path

from core.grid_calculator import calc_layout_geometry
from core.llm_client import call_llm, call_llm_async
from core.config import MODEL_DESIGNER, PROMPTS_DIR
from core.prompt_assembler import assemble_prompt
from core.grid_calculator import calc_layout_geometry
from models.contracts import LayoutPlan, SlideClassificationV2, DesignedSlide

logger = logging.getLogger(__name__)

MAX_PARALLEL = 5

FALLBACK_SVG = '<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg"><rect width="1280" height="720" fill="#FFFFFF"/><text x="640" y="360" text-anchor="middle" font-size="24" fill="#1A1A1A">Design generation failed</text></svg>'


def _build_system_prompt(classification: SlideClassificationV2) -> str:
    """Собирает системный промпт: шаблон + design rules."""
    prompt_path = PROMPTS_DIR / "junior_designer.md"
    raw = prompt_path.read_text(encoding="utf-8")

    # Убираем плейсхолдеры из системного промпта — они пойдут в user message
    # Оставляем только инструкции до плейсхолдеров
    cut = raw.find("## LAYOUT GEOMETRY")
    if cut != -1:
        template = raw[:cut].strip()
    else:
        template = raw

    design_rules = assemble_prompt(classification)
    return f"{template}\n\n## DESIGN RULES\n{design_rules}"


def _build_user_message(layout_plan: LayoutPlan) -> str:
    """Данные конкретного слайда для user message."""
    return f"## LAYOUT PLAN\n{layout_plan.model_dump_json(indent=2)}"


def _extract_svg(raw: str, slide_idx: int) -> str:
    """Извлекает SVG из ответа LLM."""
    start = raw.find("<svg")
    end = raw.find("</svg>")
    if start != -1 and end != -1:
        return raw[start:end + 6]
    logger.warning(f"SVG не найден для слайда {slide_idx}")
    return FALLBACK_SVG


def _save_svg(slide_idx: int, svg_code: str) -> Path:
    """Сохраняет SVG файл."""
    svg_dir = Path("temp/svg")
    svg_dir.mkdir(parents=True, exist_ok=True)
    path = svg_dir / f"slide_{slide_idx}.svg"
    path.write_text(svg_code, encoding="utf-8")
    return path


def design_slide_junior(
    layout_plan: LayoutPlan,
    classification: SlideClassificationV2,
    accent_color: str = "#0066CC"
) -> DesignedSlide:
    """Синхронная генерация SVG для одного слайда."""
    idx = layout_plan.slide_index
    logger.info(f"Junior Designer: слайд {idx}")

    try:
        system_prompt = _build_system_prompt(classification)
        user_msg = _build_user_message(layout_plan)

        raw = call_llm(
            prompt=user_msg,
            model_name=MODEL_DESIGNER,
            system_instruction=system_prompt
        )

        svg_code = _extract_svg(raw, idx)
        _save_svg(idx, svg_code)
        logger.info(f"Слайд {idx}: SVG готов ({len(svg_code)} символов)")
        return DesignedSlide(slide_index=idx, svg_code=svg_code)

    except Exception as e:
        logger.error(f"Ошибка Junior для слайда {idx}: {e}")
        return DesignedSlide(slide_index=idx, svg_code=FALLBACK_SVG)


async def _design_one_async(
    layout_plan: LayoutPlan,
    classification: SlideClassificationV2,
    semaphore: asyncio.Semaphore
) -> DesignedSlide:
    """Async генерация одного слайда."""
    idx = layout_plan.slide_index
    logger.info(f"Junior async: старт слайда {idx}")

    try:
        system_prompt = _build_system_prompt(classification)
        user_msg = _build_user_message(layout_plan)

        raw = await call_llm_async(
            prompt=user_msg,
            model_name=MODEL_DESIGNER,
            system_instruction=system_prompt,
            semaphore=semaphore
        )

        svg_code = _extract_svg(raw, idx)
        _save_svg(idx, svg_code)
        logger.info(f"Слайд {idx}: SVG готов ({len(svg_code)} символов)")
        return DesignedSlide(slide_index=idx, svg_code=svg_code)

    except Exception as e:
        logger.error(f"Ошибка async Junior для слайда {idx}: {e}")
        return DesignedSlide(slide_index=idx, svg_code=FALLBACK_SVG)


async def design_all_junior_async(
    layout_plans: list[LayoutPlan],
    classifications: list[SlideClassificationV2],
    accent_color: str = "#0066CC"
) -> list[DesignedSlide]:
    """Параллельная генерация SVG для всех слайдов (до MAX_PARALLEL одновременно)."""
    logger.info(f"Junior async: {len(layout_plans)} слайдов, параллельность={MAX_PARALLEL}")

    semaphore = asyncio.Semaphore(MAX_PARALLEL)

    tasks = [
        _design_one_async(plan, cls, semaphore)
        for plan, cls in zip(layout_plans, classifications)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Обработка ошибок
    final = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error(f"Слайд {i} упал: {r}")
            final.append(DesignedSlide(slide_index=i, svg_code=FALLBACK_SVG))
        else:
            final.append(r)

    # Сортируем по slide_index
    final.sort(key=lambda x: x.slide_index)
    return final


def design_all_junior(
    layout_plans: list[LayoutPlan],
    classifications: list[SlideClassificationV2],
    accent_color: str = "#0066CC"
) -> list[DesignedSlide]:
    """Обёртка: запускает async параллельность из синхронного кода."""
    return asyncio.run(
        design_all_junior_async(layout_plans, classifications, accent_color)
    )


if __name__ == "__main__":
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich
    from agents.classifier import classify_slide_v2
    from agents.senior_designer import design_slide_senior

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    logger.info(f"Тест Junior Designer: {pptx_path}")

    images = render_slides(pptx_path)
    parsed = parse_pptx_rich(pptx_path)

    if not images or not parsed:
        logger.error("Нет данных")
        sys.exit(1)

    # Один слайд — полный пайплайн
    cls = classify_slide_v2(images[0], parsed.slides[0].model_dump(), slide_index=0)
    plan = design_slide_senior(cls, parsed.slides[0].model_dump())
    result = design_slide_junior(plan, cls)

    print(f"\nSVG длина: {len(result.svg_code)}")
    print(f"Файл: temp/svg/slide_0.svg")