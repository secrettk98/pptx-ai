"""Тест: прогоняем 1 слайд через Vision → Parser → Classifier → JSON_FINAL."""

import json
import sys
from pathlib import Path

# Чтобы импорты работали из корня проекта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.logger import get_logger
from parsers.slide_renderer import render_slides
from parsers.pptx_parser import parse_pptx_rich
from agents.vision_classifier import classify_slide
from agents.classifier import classify_slide_final

log = get_logger("test_classifier")


def main():
    # 1. Путь к PPTX
    pptx_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    log.info(f"PPTX: {pptx_path}")

    # 2. Рендерим слайды в JPG
    log.info("Рендерим слайды...")
    images = render_slides(pptx_path)
    log.info(f"Получено {len(images)} картинок")

    # Берём только слайд 0
    image_path = images[0]
    log.info(f"Тестируем слайд 0: {image_path}")

    # 3. Vision — AI смотрит на картинку
    log.info("Запуск Vision classifier...")
    json_vision = classify_slide(image_path, slide_index=0)
    log.info(f"Vision готов. Тип: {json_vision.get('slide_type')}, групп: {len(json_vision.get('groups', []))}")

    # 4. Parser — Python читает PPTX
    log.info("Запуск Rich парсера...")
    parsed = parse_pptx_rich(pptx_path)
    json_parsed = parsed.slides[0].model_dump()
    log.info(f"Парсер готов. Элементов: {len(json_parsed.get('shapes', []))}")

    # 5. Classifier — объединяем Vision + Parser → JSON_FINAL
    log.info("Запуск Classifier...")
    result = classify_slide_final(json_vision, json_parsed, slide_index=0)

    # 6. Выводим результат
    print("\n" + "=" * 60)
    print("JSON_FINAL")
    print("=" * 60)
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("СВОДКА")
    print("=" * 60)
    print(f"  Тип слайда:  {result.slide_type}")
    print(f"  Сложность:   {result.complexity}")
    print(f"  Групп:       {len(result.groups)}")
    print(f"  Палитра:     BG={result.color_palette.background}  Primary={result.color_palette.primary}")
    print(f"  Reverse:     {result.reverse_summary if result.reverse_summary else 'нет'}")

    for g in result.groups:
        elems = ", ".join([e.type for e in g.elements])
        print(f"  [{g.group_id}] {g.role} ({g.zone}) -> {elems}")
        if g.reverse_type:
            print(f"         reverse: {g.reverse_type} / {g.reverse_action} — {g.reverse_reason}")


if __name__ == "__main__":
    main()