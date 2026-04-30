"""Модуль генерации SVG-макетов слайдов на основе текстовых брифов с использованием LLM."""

import time
from pathlib import Path

from core.llm_client import call_llm
from core.config import MODEL_DESIGNER, PROMPTS_DIR, TEMP_DIR, CONFIG_DIR
from core.logger import get_logger
from models.contracts import SlideBrief, DesignedSlide

log = get_logger(__name__)

FALLBACK_SVG: str = (
    '<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
    '<rect width="1280" height="720" fill="#FFFFFF"/>'
    '<text x="640" y="360" text-anchor="middle" font-size="24" fill="#1A1A1A">'
    'Design generation failed</text></svg>'
)


def design_slide(brief: SlideBrief, accent_color: str) -> DesignedSlide:
    """Генерирует SVG-код для одного слайда по заданному брифу и акцентному цвету."""
    try:
        prompt_path = PROMPTS_DIR / "designer.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")

        # Читаем Layout Code и Design Code
        layout_code_path = CONFIG_DIR / "layout_code.md"
        design_code_path = CONFIG_DIR / "design_code_style1.md"
        layout_code = (
            layout_code_path.read_text(encoding="utf-8")
            if layout_code_path.exists()
            else ""
        )
        design_code = (
            design_code_path.read_text(encoding="utf-8")
            if design_code_path.exists()
            else ""
        )

        # Подготовка промпта через замену плейсхолдеров
        prompt = (
            prompt_template.replace("{accent_color}", accent_color)
            .replace("{slide_index}", str(brief.slide_index))
            .replace("{layout_name}", brief.layout_name)
            .replace("{headline}", brief.headline)
            .replace("{key_points}", ", ".join(brief.key_points))
            .replace("{visual_hint}", brief.visual_hint)
            .replace("{priority_order}", ", ".join(brief.priority_order))
            .replace("{layout_code}", layout_code)
            .replace("{design_code}", design_code)
        )


        log.info(f"  Designing slide {brief.slide_index}...")
        raw_svg = call_llm(prompt=prompt, model_name=MODEL_DESIGNER)

        # Очистка от markdown блоков
        svg_code = raw_svg.strip()
        if "```svg" in svg_code:
            start_idx = svg_code.find("<svg")
            end_idx = svg_code.rfind("</svg>") + 6
            svg_code = svg_code[start_idx:end_idx]
        elif "```" in svg_code:
            start_idx = svg_code.find("<svg")
            svg_code = svg_code[start_idx:]

        # Сохранение результата во временную папку
        svg_dir = TEMP_DIR / "svg"
        svg_dir.mkdir(parents=True, exist_ok=True)
        svg_path = svg_dir / f"slide_{brief.slide_index}.svg"
        svg_path.write_text(svg_code, encoding="utf-8")

        log.info(f"  Saved: {svg_path.name}")
        return DesignedSlide(slide_index=brief.slide_index, svg_code=svg_code)

    except Exception as e:
        log.error(f"Ошибка при проектировании слайда {brief.slide_index}: {e}")
        return DesignedSlide(slide_index=brief.slide_index, svg_code=FALLBACK_SVG)


def design_all(briefs: list[SlideBrief], accent_color: str) -> list[DesignedSlide]:
    """Последовательно генерирует дизайн для всех слайдов из списка брифов."""
    results: list[DesignedSlide] = []
    for brief in briefs:
        result = design_slide(brief, accent_color)
        results.append(result)
        # Ожидание для соблюдения лимитов API
        time.sleep(3)
    return results


if __name__ == "__main__":
    test_brief = SlideBrief(
        slide_index=0,
        layout_name="text_focus",
        headline="TEST SLIDE",
        key_points=["Point 1", "Point 2"],
        visual_hint="Simple layout",
        remove=[],
        priority_order=["headline", "points"],
    )

    res = design_slide(test_brief, "#0066CC")
    print(f"SVG length: {len(res.svg_code)}")
    print(f"First 200 chars: {res.svg_code[:200]}")