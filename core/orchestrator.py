"""Главный оркестратор пайплайна редизайна презентаций."""

import shutil
from pathlib import Path
from core.logger import get_logger
from core.config import TEMP_DIR, OUTPUT_DIR
from parsers.pptx_parser import parse_pptx
from parsers.slide_renderer import render_slides
from agents.vision_classifier import classify_all
from agents.brain import get_strategy, get_briefs
from agents.designer import design_all

log = get_logger("orchestrator")


def run_redesign(input_pptx: str, accent_color: str = "#0066CC", mode: str = "pitch") -> str:
    """Запускает полный цикл редизайна презентации и возвращает путь к результату."""
    input_path = Path(input_pptx)
    
    # Очистка temp перед запуском
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(exist_ok=True)
    log.info("Temp directory cleaned")
    
    log.info("=== PPTX-AI Redesign Pipeline ===")
    log.info(f"Input: {input_path.name}, Accent: {accent_color}, Mode: {mode}")

    # Шаг 1: Принять входные данные
    log.info("Step 1/15: Input received")

    # Шаг 2: Парсинг PPTX
    log.info("Step 2/15: Parsing PPTX...")
    parsed = parse_pptx(input_path)
    log.info(f"  Found {parsed.slide_count} slides")

    # Шаг 3: Конвертация слайдов в JPG
    log.info("Step 3/15: Converting slides to JPG...")
    slide_images = render_slides(input_path)
    log.info(f"  Rendered {len(slide_images)} images")

    # Шаг 4: Vision-классификация
    log.info("Step 4/15: Classifying slides...")
    classifications = classify_all(slide_images)
    for c in classifications:
        log.info(f"  Slide {c.slide_index}: {c.slide_type} (map={c.has_map}, chart={c.has_chart})")

    # Шаг 5: Мозг — стратегия и брифы
    log.info("Step 5/15: Brain — strategy & briefs...")
    strategy = get_strategy(parsed, classifications, accent_color, mode)
    log.info(f"  Strategy: {strategy.presentation_type}, audience: {strategy.audience}")
    briefs = get_briefs(parsed, classifications, strategy)
    for b in briefs:
        log.info(f"  Brief slide {b.slide_index}: {b.layout_name} — {b.headline[:50]}")

    # Шаг 6: Подбор шаблонов
    log.info("Step 6/15: Template matching...")
    # TODO: agents.template_matcher

    # Шаг 7: Тест шаблонов
    log.info("Step 7/15: Template testing...")
    # TODO: жёсткий шаблон если >0.85

    # Шаг 8: Дизайнер — генерация SVG
    log.info("Step 8/15: Designer — generating SVG...")
    designed_slides = design_all(briefs, accent_color)
    log.info(f"  Designed {len(designed_slides)} slides")

    # Шаг 9: Реверс-инжиниринг (карты/графики/схемы)
    log.info("Step 9/15: Reverse engineering complex elements...")
    # TODO: reverse modules

    # Шаг 10: Художник — AI-изображения
    log.info("Step 10/15: Artist — generating images...")
    # TODO: agents.artist

    # Шаг 11: Постобработка SVG
    log.info("Step 11/15: SVG post-processing...")
    # TODO: ppt_master.finalize_svg

    # Шаг 12: PPT Master — SVG to PPTX
    log.info("Step 12/15: PPT Master — SVG to PPTX...")
    # TODO: ppt_master.svg_to_pptx

    # Шаг 13: Сборка финального PPTX
    log.info("Step 13/15: Assembling final PPTX...")
    # TODO: сборка

    # Шаг 14: Инспектор
    log.info("Step 14/15: Inspector — quality check...")
    # TODO: agents.inspector

    # Шаг 15: Готово
    output_path = OUTPUT_DIR / f"redesigned_{input_path.name}"
    log.info(f"Step 15/15: Done! Output: {output_path}")

    return str(output_path)