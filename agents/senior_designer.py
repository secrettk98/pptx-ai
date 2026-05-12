"""Агент Senior Designer для генерации инструкций по дизайну слайдов."""

import json
import logging
import time

from core.llm_client import call_llm
from core.config import MODEL_BRAIN, PROMPTS_DIR, CONFIG_DIR
from models.contracts import SlideClassificationFinal, DesignInstruction

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)


def design_slide_senior(classification: SlideClassificationFinal, accent_color: str) -> DesignInstruction:
    try:
        logger.info(f"Планирование дизайна для слайда {classification.slide_index}")
        
        prompt_path = PROMPTS_DIR / "senior_designer.md"
        layout_path = CONFIG_DIR / "layout_code.md"
        design_path = CONFIG_DIR / "design_code_style1.md"
        
        prompt_template = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        layout_code = layout_path.read_text(encoding="utf-8") if layout_path.exists() else ""
        design_code = design_path.read_text(encoding="utf-8") if design_path.exists() else ""
        
        json_final = classification.model_dump_json(indent=2)
        
        prompt = prompt_template.replace("{json_final}", json_final)
        prompt = prompt.replace("{accent_color}", accent_color)
        prompt = prompt.replace("{layout_code}", layout_code)
        prompt = prompt.replace("{design_code}", design_code)
        
        raw_response = call_llm(prompt=prompt, model_name=MODEL_BRAIN, json_mode=True)
        
        clean_response = raw_response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        elif clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        data = json.loads(clean_response)
        data.pop("slide_index", None)
        
        from core.llm_normalize import normalize_for_model
        data = normalize_for_model(data, DesignInstruction)
        instruction = DesignInstruction(slide_index=classification.slide_index, **data)
        
        logger.info(f"Дизайн спланирован. layout: {instruction.layout_name}, блоков: {len(instruction.blocks)}")
        return instruction
        
    except Exception as e:
        logger.error(f"Ошибка при планировании дизайна для слайда {classification.slide_index}: {e}")
        raise


def design_all_senior(classifications: list[SlideClassificationFinal], accent_color: str) -> list[DesignInstruction]:
    try:
        logger.info(f"Запуск пакетного планирования для {len(classifications)} слайдов")
        instructions = []
        for i, classification in enumerate(classifications):
            instruction = design_slide_senior(classification, accent_color)
            instructions.append(instruction)
            if i < len(classifications) - 1:
                time.sleep(2)
        return instructions
    except Exception as e:
        logger.error(f"Сбой при массовом планировании дизайна: {e}")
        raise


if __name__ == "__main__":
    logger.info("Запуск тестового прогона Senior Designer")
    
    test_classification = SlideClassificationFinal(
        slide_index=0,
        slide_type="content",
        complexity="low",
        groups=[{"group_id": 1, "elements": []}],
        reverse_summary="Тестовый слайд"
    )
    
    try:
        result = design_slide_senior(test_classification, "#0066CC")
        print("\n--- Результат ---")
        print(f"layout_name: {result.layout_name}")
        print(f"Количество блоков: {len(result.blocks)}")
    except Exception as e:
        logger.error(f"Тестовый прогон завершился с ошибкой: {e}")