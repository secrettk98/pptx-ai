"""Агент для финальной классификации слайдов на основе данных Vision и Parser."""

import json
import logging
import time
from pathlib import Path

from core.llm_client import call_llm
from core.config import PROMPTS_DIR
from models.contracts import SlideClassificationFinal

logger = logging.getLogger(__name__)

from core.config import MODEL_CLASSIFIER
MODEL_NAME = MODEL_CLASSIFIER

def classify_slide_final(json_vision: dict, json_parsed: dict, slide_index: int) -> SlideClassificationFinal:
    """Объединяет JSON_VISION и JSON_PARSED в финальную классификацию с помощью LLM."""
    logger.info(f"Начало финальной классификации для слайда {slide_index}")
    
    try:
        prompt_path = PROMPTS_DIR / "classifier.md"
        system_prompt = prompt_path.read_text(encoding="utf-8")
        
        vision_str = json.dumps(json_vision, ensure_ascii=False, indent=2)
        parsed_str = json.dumps(json_parsed, ensure_ascii=False, indent=2)
        
        prompt = f"{system_prompt}\n\n# INPUT\n\n## JSON_VISION\n{vision_str}\n\n## JSON_PARSED\n{parsed_str}"
        
        logger.info(f"Вызов LLM {MODEL_NAME} для классификации (JSON mode)")
        response = call_llm(prompt=prompt, model_name=MODEL_NAME, json_mode=True)
        
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        elif clean_response.startswith("```"):
            clean_response = clean_response[3:]
            
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
            
        data = json.loads(clean_response.strip())
        data.pop("slide_index", None)
        
        from core.llm_normalize import normalize_for_model
        data = normalize_for_model(data, SlideClassificationFinal)
        result = SlideClassificationFinal(slide_index=slide_index, **data)
        logger.info(f"Слайд {slide_index} успешно классифицирован (тип: {result.slide_type}, групп: {len(result.groups)})")
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при финальной классификации слайда {slide_index}: {e}")
        raise


def classify_all_final(vision_results: list[dict], parsed_results: list[dict]) -> list[SlideClassificationFinal]:
    """Пакетная обработка всех слайдов для получения финальной классификации."""
    logger.info(f"Запуск пакетной классификации для {len(vision_results)} слайдов")
    results = []
    
    try:
        for idx, (vision, parsed) in enumerate(zip(vision_results, parsed_results)):
            if idx > 0:
                logger.info("Ожидание 2 секунды перед следующим вызовом API...")
                time.sleep(2)
                
            result = classify_slide_final(vision, parsed, slide_index=idx)
            results.append(result)
            
        logger.info("Пакетная классификация успешно завершена")
        return results
        
    except Exception as e:
        logger.error(f"Сбой в процессе пакетной классификации: {e}")
        raise