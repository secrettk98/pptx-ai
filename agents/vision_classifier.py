"""Модуль для классификации слайдов по их изображениям с использованием LLM."""

import json
import sys
import time
from pathlib import Path

from core.llm_client import call_llm
from core.config import MODEL_VISION, PROMPTS_DIR
from core.logger import get_logger
from models.contracts import SlideClassification

log = get_logger(__name__)


def classify_slide(image_path: str | Path, slide_index: int) -> SlideClassification:
    """Классифицирует тип слайда по его изображению через вызов LLM."""
    try:
        prompt_path = PROMPTS_DIR / "vision_classifier.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        
        log.info(f"Classifying slide {slide_index}: {Path(image_path).name}")
        
        raw = call_llm(
            prompt=prompt, 
            model_name=MODEL_VISION, 
            image_path=str(image_path), 
            json_mode=True
        )
        
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        
        result = SlideClassification(slide_index=slide_index, **data)
        log.info(f"  Slide {slide_index}: {result.slide_type} (confidence: {result.confidence})")
        
        return result
    except Exception as e:
        log.error(f"Ошибка при классификации слайда {slide_index} из файла {image_path}: {e}")
        raise


def classify_all(image_paths: list[Path]) -> list[SlideClassification]:
    """Выполняет поочередную классификацию переданного списка изображений слайдов."""
    try:
        results = []
        for idx, img_path in enumerate(image_paths):
            result = classify_slide(img_path, idx)
            results.append(result)
            time.sleep(3)
        return results
    except Exception as e:
        log.error(f"Ошибка в процессе пакетной классификации слайдов: {e}")
        raise


if __name__ == "__main__":
    from parsers.slide_renderer import render_slides
    
    try:
        pptx = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
        images = render_slides(pptx)
        results = classify_all(images)
        
        for r in results:
            print(f"Slide {r.slide_index}: {r.slide_type} | map={r.has_map} chart={r.has_chart} | {r.confidence}")
    except Exception as e:
        log.error(f"Сбой при выполнении модуля классификации: {e}")