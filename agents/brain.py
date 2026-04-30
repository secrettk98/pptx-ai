"""Арт-директор (Brain): анализ презентации, формирование стратегии и брифов."""

import json
from pathlib import Path
from core.llm_client import call_llm
from core.config import MODEL_BRAIN, PROMPTS_DIR
from core.logger import get_logger
from models.contracts import PresentationStructure, SlideClassification, PresentationStrategy, SlideBrief

log = get_logger(__name__)


def get_strategy(parsed: PresentationStructure, classifications: list[SlideClassification], accent_color: str, mode: str) -> PresentationStrategy:
    """Формирует общую стратегию редизайна на основе структуры и типов слайдов."""
    try:
        prompt_template = (PROMPTS_DIR / "brain_level1.md").read_text(encoding="utf-8")
        
        overview_lines = [
            f"Slide {s.slide_index}: type={classifications[s.slide_index].slide_type}, shapes={s.shape_count}, texts={s.texts[:3]}"
            for s in parsed.slides
        ]
        slides_overview = "\n".join(overview_lines)
        
        prompt = (prompt_template
                  .replace("{filename}", parsed.filename)
                  .replace("{slide_count}", str(parsed.slide_count))
                  .replace("{accent_color}", accent_color)
                  .replace("{mode}", mode)
                  .replace("{slides_overview}", slides_overview))
        
        log.info(f"Brain Level 1: analyzing {parsed.slide_count} slides...")
        raw = call_llm(prompt=prompt, model_name=MODEL_BRAIN, json_mode=True)
        raw = raw.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(raw)
        result = PresentationStrategy(**data)
        
        log.info(f"  Strategy: {result.presentation_type}, audience: {result.audience}")
        return result
    except Exception as e:
        log.error(f"Ошибка при создании стратегии презентации: {e}")
        raise RuntimeError(f"Сбой генерации стратегии: {e}") from e


def get_briefs(parsed: PresentationStructure, classifications: list[SlideClassification], strategy: PresentationStrategy) -> list[SlideBrief]:
    """Разрабатывает детальные инструкции (брифы) для дизайна каждого слайда."""
    try:
        prompt_template = (PROMPTS_DIR / "brain_level2.md").read_text(encoding="utf-8")
        strategy_json = strategy.model_dump_json(indent=2)
        
        slides_data = [
            {
                "slide_index": s.slide_index,
                "type": classifications[s.slide_index].slide_type,
                "texts": s.texts,
                "shape_count": s.shape_count,
                "image_count": s.image_count
            }
            for s in parsed.slides
        ]
        slides_json = json.dumps(slides_data, indent=2, ensure_ascii=False)
        
        prompt = prompt_template.replace("{strategy_json}", strategy_json).replace("{slides_json}", slides_json)
        
        log.info(f"Brain Level 2: writing briefs for {parsed.slide_count} slides...")
        raw = call_llm(prompt=prompt, model_name=MODEL_BRAIN, json_mode=True)
        raw = raw.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(raw)
        briefs = [SlideBrief(**item) for item in data]
        
        for b in briefs:
            log.info(f"  Slide {b.slide_index}: layout={b.layout_name}, headline={b.headline[:50]}")
            
        return briefs
    except Exception as e:
        log.error(f"Ошибка при формировании брифов: {e}")
        raise RuntimeError(f"Сбой генерации брифов: {e}") from e


if __name__ == "__main__":
    import sys
    from parsers.pptx_parser import parse_pptx
    from parsers.slide_renderer import render_slides
    from agents.vision_classifier import classify_all
    
    pptx = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    
    try:
        parsed_data = parse_pptx(pptx)
        images = render_slides(pptx)
        classifications_data = classify_all(images)
        
        strat = get_strategy(parsed_data, classifications_data, "#0066CC", "pitch")
        print(f"\nStrategy: {strat.model_dump_json(indent=2)}")
        
        brief_list = get_briefs(parsed_data, classifications_data, strat)
        print(f"\nBriefs:")
        for brief in brief_list:
            print(f"  Slide {brief.slide_index}: {brief.headline}")
    except Exception as err:
        print(f"Ошибка выполнения: {err}")