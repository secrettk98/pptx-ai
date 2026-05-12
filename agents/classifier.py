"""Агент для классификации слайдов на основе изображения и распарсенных данных."""

import json
import logging
import time
import sys
from pathlib import Path

from core.llm_client import call_llm
from core.config import MODEL_CLASSIFIER, CONFIG_DIR
from core.llm_normalize import normalize_for_model
from models.contracts import SlideClassificationV2

logger = logging.getLogger(__name__)


def _get_core_rules_section_1() -> str:
    """Извлекает секцию §1 из файла core_rules.md для контекста."""
    try:
        rules_path = CONFIG_DIR / "core_rules.md"
        if not rules_path.exists():
            logger.warning(f"Файл правил {rules_path} не найден")
            return ""
            
        content = rules_path.read_text(encoding="utf-8")
        start_idx = content.find("§1")
        if start_idx == -1:
            return content
            
        end_idx = content.find("§2", start_idx)
        if end_idx == -1:
            return content[start_idx:]
            
        return content[start_idx:end_idx]
    except Exception as e:
        logger.error(f"Ошибка при чтении core_rules.md: {e}")
        return ""


def classify_slide_v2(image_path: str, parsed_slide: dict, slide_index: int, user_header_pref: str = "auto") -> SlideClassificationV2:
    """Классифицирует слайд на основе изображения и распарсенных данных."""
    logger.info(f"Начало классификации для слайда {slide_index}")
    
    try:
        classifier_path = CONFIG_DIR / "classifier.md"
        classifier_prompt = classifier_path.read_text(encoding="utf-8")
        
        logger.info("Чтение секции §1 из core_rules.md")
        rules_context = _get_core_rules_section_1()
        
        parsed_str = json.dumps(parsed_slide, ensure_ascii=False, indent=2)
        prompt = f"{classifier_prompt}\n\n# CORE RULES CONTEXT\n{rules_context}\n\n# PARSED DATA\n{parsed_str}\n\n# USER HEADER PREFERENCE\n{user_header_pref}"
        
        logger.info(f"Вызов LLM {MODEL_CLASSIFIER} для классификации слайда {slide_index}")
        raw_response = call_llm(
            prompt=prompt, 
            model_name=MODEL_CLASSIFIER, 
            image_path=image_path, 
            json_mode=True
        )
        
        logger.info("Очистка ответа от Markdown-разметки")
        clean_response = raw_response.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(clean_response)
        data.pop("slide_index", None)
        
        logger.info("Нормализация ответа под модель SlideClassificationV2")
        data = normalize_for_model(data, SlideClassificationV2)
        result = SlideClassificationV2(slide_index=slide_index, **data)
        
        logger.info(f"Слайд {slide_index} классифицирован: role={result.slide_role}, objects={len(result.objects)}, header={result.header_type}")
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при классификации слайда {slide_index}: {e}")
        raise


def classify_all_v2(image_paths: list[str], parsed_slides: list[dict], user_header_pref: str = "auto") -> list[SlideClassificationV2]:
    """Пакетная классификация всех переданных слайдов."""
    logger.info(f"Запуск пакетной классификации для {len(image_paths)} слайдов")
    results = []
    
    try:
        for idx, (img_path, parsed) in enumerate(zip(image_paths, parsed_slides)):
            if idx > 0:
                logger.info("Ожидание 2 секунды перед следующим вызовом API")
                time.sleep(2)
                
            result = classify_slide_v2(img_path, parsed, slide_index=idx, user_header_pref=user_header_pref)
            results.append(result)
            
        logger.info("Пакетная классификация успешно завершена")
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при пакетной классификации: {e}")
        raise


if __name__ == "__main__":
    from parsers.slide_renderer import render_slides
    from parsers.pptx_parser import parse_pptx_rich
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    
    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    logger.info(f"Запуск тестовой классификации для: {pptx_path}")
    
    try:
        logger.info("Рендеринг слайдов")
        test_images = render_slides(pptx_path)
        
        logger.info("Парсинг содержимого слайдов")
        parsed_presentation = parse_pptx_rich(pptx_path)
        
        if not test_images or not parsed_presentation:
            logger.error("Не удалось получить данные для классификации")
            sys.exit(1)
            
        # ParsedPresentation - это объект (Pydantic), обращаемся к атрибуту slides
        # Метод принимает dict, поэтому используем model_dump()
        first_slide_parsed = parsed_presentation.slides[0].model_dump()
        
        test_result = classify_slide_v2(test_images[0], first_slide_parsed, slide_index=0)
        
        print(f"slide_role: {test_result.slide_role}")
        print(f"objects: {len(test_result.objects)}")
        print(f"visual_subtype: {test_result.visual_subtype}")
        print(f"header_type: {test_result.header_type}")
        print(f"style_mode: {test_result.style_mode}")
        print(f"objects list: {test_result.objects}")
        
    except Exception as err:
        logger.error(f"Ошибка в блоке тестирования: {err}")