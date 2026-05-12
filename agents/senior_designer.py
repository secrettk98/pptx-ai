"""Агент Senior Designer для планирования композиции слайда (v2)."""

import json
import logging
import time
import sys
from pathlib import Path

from core.llm_client import call_llm
from core.config import MODEL_BRAIN, PROMPTS_DIR
from core.llm_normalize import normalize_for_model
from core.prompt_assembler import assemble_prompt
from models.contracts import SlideClassificationV2, LayoutPlan

logger = logging.getLogger(__name__)


def design_slide_senior(classification: SlideClassificationV2, parsed_slide: dict, accent_color: str = "#0066CC") -> LayoutPlan:
    """Генерирует план композиции (LayoutPlan) для одного слайда."""
    logger.info(f"Начало планирования дизайна для слайда {classification.slide_index}")
    
    try:
        prompt_path = PROMPTS_DIR / "senior_designer.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")
        
        logger.info("Сборка контекста правил дизайна")
        assembled_rules = assemble_prompt(classification)
        
        parsed_str = json.dumps(parsed_slide, ensure_ascii=False, indent=2)
        class_str = classification.model_dump_json(indent=2)
        
        full_prompt = (
            f"{prompt_template}\n\n"
            f"# DESIGN RULES\n{assembled_rules}\n\n"
            f"# CLASSIFICATION\n{class_str}\n\n"
            f"# PARSED CONTENT\n{parsed_str}\n\n"
            f"# ACCENT COLOR\n{accent_color}"
        )
        
        logger.info(f"Вызов LLM {MODEL_BRAIN} для генерации композиции")
        raw_response = call_llm(
            prompt=full_prompt, 
            model_name=MODEL_BRAIN, 
            json_mode=True
        )
        
        logger.info("Парсинг и нормализация ответа LLM")
        clean_response = raw_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_response)
        
        data.pop("slide_index", None)
        data = normalize_for_model(data, LayoutPlan)
        result = LayoutPlan(slide_index=classification.slide_index, **data)
        
        rows_count = len(result.rows) if hasattr(result, "rows") and result.rows else 0
        logger.info(f"Дизайн для слайда {classification.slide_index} готов: схема {result.composition_schema}, строк: {rows_count}")
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при планировании дизайна слайда {classification.slide_index}: {e}")
        raise


def design_all_senior(classifications: list[SlideClassificationV2], parsed_slides: list[dict], accent_color: str = "#0066CC") -> list[LayoutPlan]:
    """Пакетное планирование композиции для списка слайдов."""
    logger.info(f"Запуск пакетного планирования для {len(classifications)} слайдов")
    results = []
    
    try:
        for idx, (classification, parsed) in enumerate(zip(classifications, parsed_slides)):
            if idx > 0:
                logger.info("Ожидание 2 секунды перед следующим вызовом API")
                time.sleep(2)
                
            result = design_slide_senior(classification, parsed, accent_color)
            results.append(result)
            
        logger.info("Пакетное планирование успешно завершено")
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при пакетном планировании дизайна: {e}")
        raise


if __name__ == "__main__":
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich
    from agents.classifier import classify_slide_v2
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    
    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    logger.info(f"Тестовый запуск пайплайна до Senior Designer для файла: {pptx_path}")
    
    try:
        logger.info("Шаг 1. Рендеринг")
        test_images = render_slides(pptx_path)
        
        logger.info("Шаг 2. Парсинг")
        test_parsed = parse_pptx_rich(pptx_path)
        
        if not test_images or not test_parsed:
            logger.error("Не удалось извлечь данные из презентации")
            sys.exit(1)
            
        logger.info("Шаг 3. Классификация первого слайда")
        test_classification = classify_slide_v2(test_images[0], test_parsed[0], slide_index=0)
        
        logger.info("Шаг 4. Senior Designer")
        layout_plan = design_slide_senior(test_classification, test_parsed[0])
        
        print("\n=== Результат LayoutPlan (JSON) ===")
        print(layout_plan.model_dump_json(indent=2))
        
        rows_cnt = len(layout_plan.rows) if layout_plan.rows else 0
        cols_cnt = sum(len(row.columns) for row in layout_plan.rows) if layout_plan.rows else 0
        
        print("\n=== Сводка ===")
        print(f"composition_schema: {layout_plan.composition_schema}")
        print(f"Количество строк: {rows_cnt}")
        print(f"Всего колонок: {cols_cnt}")
        
    except Exception as err:
        logger.error(f"Ошибка в блоке тестирования: {err}")