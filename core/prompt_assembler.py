"""Сборщик design rules из модульных конфигов."""

import logging
from pathlib import Path

from core.config import CONFIG_DIR
from models.contracts import PresentationStrategy

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


def assemble_rules(strategy: PresentationStrategy) -> str:
    """Собирает design rules из модулей на основе Strategy.
    
    Грузит ВСЕ модули, т.к. Architect определяет объекты сам.
    """
    logger.info("Сборка design rules")
    parts = []

    # 1. Core rules — всегда
    core_text = _read_module("core_rules.md")
    if core_text:
        parts.append(core_text)

    # 2. Style — по strategy.style_mode
    if strategy.style_mode == "strict":
        style_text = _read_module("styles/strict.md")
    else:
        style_text = _read_module("styles/soft.md")
    if style_text:
        parts.append(style_text)

    # 3. Header — по strategy.header_type
    header_key = "A" if strategy.header_type == "fixed" else "B"
    header_map = {
        "A": "headers/type_a_rigid.md",
        "B": "headers/type_b_floating.md",
        "C": "headers/type_c_top.md",
    }
    if header_key in header_map:
        header_text = _read_module(header_map[header_key])
        if header_text:
            parts.append(header_text)

    # 4. Card rules — всегда (Architect сам определит нужны ли карточки)
    card_text = _read_module("card.md")
    if card_text:
        parts.append(card_text)

    # 5. Patterns — всегда
    pattern_text = _read_module("patterns.md")
    if pattern_text:
        parts.append(pattern_text)

    logger.info(f"Собрано {len(parts)} модулей design rules")
    return "\n\n---\n\n".join(parts)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    test_strategy = PresentationStrategy(
        header_type="floating",
        style_mode="soft",
        accent_color="#0066CC",
        presentation_mode="formal",
        allow_rewrite=False
    )

    rules = assemble_rules(test_strategy)
    print(f"Rules собраны: {len(rules)} символов")
    if rules:
        print(f"Начало: {rules[:200]}")