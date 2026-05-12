"""Сборщик промптов для генератора SVG на основе классификации слайда."""

import logging
from pathlib import Path

from core.config import CONFIG_DIR
from models.contracts import SlideClassificationV2

logger = logging.getLogger(__name__)


def _read_module(relative_path: str) -> str:
    """Читает markdown файл из директории конфигурации."""
    try:
        path = CONFIG_DIR / relative_path
        if not path.exists():
            logger.warning(f"Модуль не найден: {path}")
            return ""
            
        text = path.read_text(encoding="utf-8")
        logger.info(f"Загружен модуль: {relative_path} ({len(text)} символов)")
        return text
    except Exception as e:
        logger.error(f"Ошибка при чтении модуля {relative_path}: {e}")
        return ""


def assemble_prompt(classification: SlideClassificationV2) -> str:
    """Собирает финальный промпт из модулей по результатам классификации."""
    logger.info(f"Начало сборки промпта для слайда {classification.slide_index}")
    parts = []

    core_text = _read_module("core_rules.md")
    if core_text:
        parts.append(core_text)

    if classification.style_mode == "strict":
        style_text = _read_module("styles/strict.md")
    else:
        style_text = _read_module("styles/soft.md")
    if style_text:
        parts.append(style_text)

    header_map = {
        "A": "headers/type_a_rigid.md",
        "B": "headers/type_b_floating.md",
        "C": "headers/type_c_top.md",
    }
    if classification.header_type in header_map:
        header_text = _read_module(header_map[classification.header_type])
        if header_text:
            parts.append(header_text)

    if "card" in classification.objects:
        card_text = _read_module("card.md")
        if card_text:
            parts.append(card_text)

    if classification.visual_subtype == "pattern":
        pattern_text = _read_module("patterns.md")
        if pattern_text:
            parts.append(pattern_text)

    logger.info(f"Собран промпт из {len(parts)} модулей для слайда {classification.slide_index}")
    return "\n\n---\n\n".join(parts)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    
    try:
        test_class = SlideClassificationV2(
            slide_index=0,
            slide_role="content",
            objects=["heading", "text", "card", "chart"],
            visual_subtype=None,
            header_type="B",
            style_mode="soft"
        )
        
        prompt = assemble_prompt(test_class)
        
        print(f"Промпт собран: {len(prompt)} символов")
        if prompt:
            print(f"Начало: {prompt[:200]}")
            print("...")
            print(f"Конец: {prompt[-200:]}")
            
    except Exception as err:
        logger.error(f"Ошибка в блоке тестирования: {err}")