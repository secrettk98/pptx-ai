"""Модуль для визуальной классификации слайдов с выделением смысловых групп в формате сырого JSON."""

import json
import sys
import time
import logging
from pathlib import Path
from typing import Any

from core.llm_client import call_llm
from core.config import MODEL_VISION, PROMPTS_DIR

logger = logging.getLogger(__name__)


def classify_slide(image_path: str | Path, slide_index: int) -> dict[str, Any]:
    """Извлекает сырой JSON с описанием групп на слайде через вызов LLM."""
    try:
        prompt_path = PROMPTS_DIR / "vision_classifier.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        
        logger.info(f"Классификация слайда {slide_index}: {Path(image_path).name}")
        
        raw = call_llm(
            prompt=prompt, 
            model_name=MODEL_VISION, 
            image_path=str(image_path), 
            json_mode=True
        )
        
        clean_raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_raw)
        
        data["slide_index"] = slide_index
        groups_count = len(data.get("groups", []))
        
        logger.info(f"Слайд {slide_index}: {data.get('slide_type')} (найдено групп: {groups_count})")
        
        return data
        
    except Exception as e:
        logger.error(f"Ошибка при классификации слайда {slide_index} из файла {image_path}: {e}")
        raise


def classify_all(image_paths: list[Path]) -> list[dict[str, Any]]:
    """Выполняет поочередную классификацию переданного списка изображений слайдов."""
    try:
        results = []
        for idx, img_path in enumerate(image_paths):
            result = classify_slide(img_path, idx)
            results.append(result)
            time.sleep(3)
        return results
    except Exception as e:
        logger.error(f"Ошибка в процессе пакетной классификации слайдов: {e}")
        raise


if __name__ == "__main__":
    from parsers.slide_renderer import render_slides
    
    try:
        pptx = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
        images = render_slides(pptx)
        results = classify_all(images)
        
        for res in results:
            s_idx = res.get("slide_index")
            s_type = res.get("slide_type")
            groups = res.get("groups", [])
            
            logger.info(f"=== Слайд {s_idx} | Тип: {s_type} | Всего групп: {len(groups)} ===")
            for g in groups:
                g_id = g.get("group_id", "?")
                role = g.get("role", "?")
                zone = g.get("zone", "?")
                desc = g.get("description", "")[:50]
                logger.info(f"  [{g_id}] {role} ({zone}): {desc}...")
                
    except Exception as exc:
        logger.error(f"Сбой выполнения скрипта: {exc}")