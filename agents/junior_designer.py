"""Агент Junior Designer для генерации SVG-кода по инструкциям."""

import logging
import time

from core.llm_client import call_llm
from core.config import MODEL_DESIGNER, PROMPTS_DIR, TEMP_DIR
from models.contracts import DesignInstruction, DesignedSlide

FALLBACK_SVG = '<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg"><rect width="1280" height="720" fill="#FFFFFF"/><text x="640" y="360" text-anchor="middle" font-size="24" fill="#1A1A1A">Design generation failed</text></svg>'

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)


def design_slide_junior(instruction: DesignInstruction) -> DesignedSlide:
    """Генерирует SVG для слайда на основе инструкции по дизайну."""
    try:
        logger.info(f"Генерация SVG для слайда {instruction.slide_index}")
        
        prompt_path = PROMPTS_DIR / "junior_designer.md"
        prompt_template = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        
        design_json = instruction.model_dump_json(indent=2)
        prompt = prompt_template.replace("{design_instruction}", design_json)
        
        raw_response = call_llm(prompt=prompt, model_name=MODEL_DESIGNER)
        
        start_idx = raw_response.find("<svg")
        end_idx = raw_response.find("</svg>")
        
        if start_idx != -1 and end_idx != -1:
            svg_code = raw_response[start_idx:end_idx + 6]
        else:
            logger.warning(f"SVG теги не найдены в ответе для слайда {instruction.slide_index}")
            svg_code = FALLBACK_SVG
            
        svg_dir = TEMP_DIR / "svg"
        svg_dir.mkdir(parents=True, exist_ok=True)
        svg_path = svg_dir / f"slide_{instruction.slide_index}.svg"
        svg_path.write_text(svg_code, encoding="utf-8")
        
        logger.info(f"SVG сохранен, длина: {len(svg_code)} символов")
        return DesignedSlide(slide_index=instruction.slide_index, svg_code=svg_code)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации SVG для слайда {instruction.slide_index}: {e}")
        return DesignedSlide(slide_index=instruction.slide_index, svg_code=FALLBACK_SVG)


def design_all_junior(instructions: list[DesignInstruction]) -> list[DesignedSlide]:
    """Пакетная генерация SVG для списка инструкций."""
    logger.info(f"Запуск генерации SVG для {len(instructions)} слайдов")
    slides = []
    for i, instruction in enumerate(instructions):
        slide = design_slide_junior(instruction)
        slides.append(slide)
        if i < len(instructions) - 1:
            time.sleep(3)
    return slides


if __name__ == "__main__":
    logger.info("Запуск тестового прогона Junior Designer")
    
    test_instruction = DesignInstruction(
        slide_index=0,
        layout_name="test_layout",
        blocks=[
            {
                "type": "title",
                "x": 47,
                "y": 47,
                "w": 1186,
                "h": 60,
                "content": {"text": "TEST SLIDE"}
            }
        ]
    )
    
    result = design_slide_junior(test_instruction)
    print("\n--- Результат ---")
    print(f"Длина SVG: {len(result.svg_code)}")
    print(f"Первые 200 символов: {result.svg_code[:200]}")