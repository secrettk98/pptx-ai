"""Тест: Vision → Parser → Classifier → Senior Designer → Junior Designer."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.logger import get_logger
from parsers.slide_renderer import render_slides
from parsers.pptx_parser import parse_pptx_rich
from agents.vision_classifier import classify_slide
from agents.classifier import classify_slide_final
from agents.senior_designer import design_slide_senior
from agents.junior_designer import design_slide_junior

log = get_logger("test_senior")


def main():
    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    slide_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    log.info(f"PPTX: {pptx_path}, слайд: {slide_idx}")

    # 1. Рендер
    log.info("Рендерим слайды...")
    images = render_slides(pptx_path)
    image_path = images[slide_idx]

    # 2. Vision
    log.info("Vision classifier...")
    json_vision = classify_slide(image_path, slide_index=slide_idx)
    log.info(f"Vision: тип={json_vision.get('slide_type')}")

    # 3. Parser
    log.info("Rich парсер...")
    parsed = parse_pptx_rich(pptx_path)
    json_parsed = parsed.slides[slide_idx].model_dump()
    log.info(f"Парсер: {len(json_parsed.get('shapes', []))} элементов")

    # 4. Classifier
    log.info("Classifier...")
    classification = classify_slide_final(json_vision, json_parsed, slide_index=slide_idx)
    log.info(f"JSON_FINAL: тип={classification.slide_type}, групп={len(classification.groups)}")

    # 5. Senior Designer
    log.info("Senior Designer...")
    instruction = design_slide_senior(classification, accent_color="#0066CC")

    # 6. Junior Designer
    log.info("Junior Designer...")
    designed = design_slide_junior(instruction)
    log.info(f"SVG готов: {len(designed.svg_code)} символов")

    # Результат
    print("\n" + "=" * 60)
    print("DESIGN INSTRUCTION")
    print("=" * 60)
    print(json.dumps(instruction.model_dump(), indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("СВОДКА")
    print("=" * 60)
    print(f"  Layout:      {instruction.layout_name}")
    print(f"  Блоков:      {len(instruction.blocks)}")
    print(f"  SVG длина:   {len(designed.svg_code)}")
    print(f"  SVG начало:  {designed.svg_code[:150]}")
    print(f"  SVG файл:    temp/svg/slide_{slide_idx}.svg")


if __name__ == "__main__":
    main()