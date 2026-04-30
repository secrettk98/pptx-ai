"""Модуль генерации SVG-макетов слайдов на основе текстовых брифов с использованием LLM."""

import time
from pathlib import Path
from core.llm_client import call_llm
from core.config import MODEL_DESIGNER, PROMPTS_DIR, TEMP_DIR
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
        
        prompt = prompt_template.format(
            accent_color=accent_color,
            slide_index=str(brief.slide_index),
            layout_name=brief.layout_name,
            headline=brief.headline,
            key_points=", ".join(brief.key_points),
            visual_hint=brief.visual_hint,
            priority_order=", ".join(brief.priority_order)
        )
        
        log.info(f"Designing slide {brief.slide_index}: {brief.layout_name}")
        raw = call_llm(prompt=prompt, model_name=MODEL_DESIGNER)
        
        # Очистка разметки Markdown
        raw = raw.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        
        # Поиск границ SVG тега
        start_idx = raw.find("<svg")
        if start_idx == -1:
            log.error(f"SVG тег не найден в ответе для слайда {brief.slide_index}")
            svg_code = FALLBACK_SVG
        else:
            end_idx = raw.find("</svg>")
            if end_idx != -1:
                svg_code = raw[start_idx : end_idx + 6]
            else:
                svg_code = raw[start_idx:]
        
        # Сохранение результата
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
        key_points=["Point one", "Point two"],
        visual_hint="Simple layout",
        remove=[],
        priority_order=["headline", "points"]
    )
    
    test_result = design_slide(test_brief, "#0066CC")
    print(f"SVG length: {len(test_result.svg_code)}")
    print(f"First 200 chars: {test_result.svg_code[:200]}")