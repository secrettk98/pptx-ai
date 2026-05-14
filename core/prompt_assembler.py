"""
Prompt Assembler (Слой 0.5) — динамическая сборка design rules.

Принимает список recommended_modules от Semantic Editor.
Загружает ТОЛЬКО нужные .md файлы из config/, отсекая лишний контекст.
Маппинг module_key → путь хранится в MODULE_REGISTRY (единственное место правки).
"""

import logging
from pathlib import Path

from core.config import CONFIG_DIR
from models.contracts import PresentationStrategy

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════
# РЕЕСТР МОДУЛЕЙ (module_key → путь относительно CONFIG_DIR)
# Semantic Editor указывает ключи из этого реестра.
# ════════════════════════════════════════════════════════

MODULE_REGISTRY: dict[str, str] = {
    # Core — всегда подключается автоматически, не запрашивается через recommended
    "core":         "core_rules.md",

    # Стили
    "style_strict": "styles/strict.md",
    "style_soft":   "styles/soft.md",

    # Заголовки
    "header_a":     "headers/type_a_rigid.md",
    "header_b":     "headers/type_b_floating.md",
    "header_c":     "headers/type_c_top.md",

    # Визуальные модули (Слой 2)
    "card":         "card.md",
    "table":        "table.md",
    "chart":        "chart.md",
    "pattern":      "patterns.md",
    "flowchart":    "flowchart.md",
    "map":          "map.md",
    "infographic":  "infographic.md",
    "image":        "image.md",
}

# Модули, которые подключаются всегда (независимо от recommended_modules)
ALWAYS_LOADED: list[str] = ["core"]


def _read_module(key: str) -> str:
    """Читает .md файл по ключу из MODULE_REGISTRY. Возвращает '' если нет файла."""
    path_str = MODULE_REGISTRY.get(key)
    if not path_str:
        logger.warning(f"Неизвестный ключ модуля: '{key}' — пропускаем")
        return ""

    path: Path = CONFIG_DIR / path_str
    if not path.exists():
        logger.warning(f"Файл модуля не найден: {path} (ключ='{key}')")
        return ""

    try:
        text = path.read_text(encoding="utf-8")
        logger.info(f"Загружен модуль '{key}': {path.name} ({len(text)} символов)")
        return text
    except OSError as e:
        logger.error(f"Ошибка чтения модуля '{key}' ({path}): {e}")
        return ""


def _resolve_style_key(strategy: PresentationStrategy) -> str:
    """Определяет ключ стиля из Strategy."""
    return "style_strict" if strategy.style_mode == "strict" else "style_soft"


def _resolve_header_key(strategy: PresentationStrategy) -> str:
    """Определяет ключ заголовка из Strategy."""
    mapping = {"fixed": "header_a", "floating": "header_b", "top": "header_c"}
    return mapping.get(strategy.header_type, "header_b")


def assemble_prompt_context(
    recommended_modules: list[str],
    strategy: PresentationStrategy,
) -> str:
    """
    Слой 0.5: собирает design rules для Spatial Architect.

    Порядок сборки:
      1. core_rules.md (всегда)
      2. style (из strategy.style_mode)
      3. header (из strategy.header_type)
      4. визуальные модули из recommended_modules (только существующие в реестре)

    Args:
        recommended_modules: список ключей из MODULE_REGISTRY (от Semantic Editor).
        strategy: стратегия презентации (определяет стиль и тип заголовка).

    Returns:
        Единая строка со всеми правилами, разделёнными разделителями.
    """
    logger.info(
        f"Сборка контекста: recommended={recommended_modules}, "
        f"style={strategy.style_mode}, header={strategy.header_type}"
    )

    ordered_keys: list[str] = []

    # 1. Всегда: core
    ordered_keys.extend(ALWAYS_LOADED)

    # 2. Стиль — из Strategy
    ordered_keys.append(_resolve_style_key(strategy))

    # 3. Заголовок — из Strategy
    ordered_keys.append(_resolve_header_key(strategy))

    # 4. Визуальные модули — только из recommended, только известные реестру
    visual_keys = [
        k for k in recommended_modules
        if k in MODULE_REGISTRY and k not in ordered_keys
    ]
    unknown_keys = [k for k in recommended_modules if k not in MODULE_REGISTRY]
    if unknown_keys:
        logger.warning(f"Неизвестные модули от Semantic Editor: {unknown_keys}")

    ordered_keys.extend(visual_keys)

    # Загрузка
    parts: list[str] = []
    for key in ordered_keys:
        text = _read_module(key)
        if text:
            parts.append(f"<!-- MODULE: {key} -->\n{text}")

    logger.info(
        f"Собрано {len(parts)}/{len(ordered_keys)} модулей "
        f"({sum(len(p) for p in parts)} символов)"
    )
    return "\n\n---\n\n".join(parts)


def assemble_rules(strategy: PresentationStrategy) -> str:
    """
    Обратная совместимость с Architect v4 (agents/architect.py).
    Грузит все модули как раньше. Для новой архитектуры использовать assemble_prompt_context().
    """
    logger.info("assemble_rules() (legacy v4) — загрузка всех модулей")
    all_visual_keys = [
        k for k in MODULE_REGISTRY
        if k not in ALWAYS_LOADED
        and not k.startswith("style_")
        and not k.startswith("header_")
    ]
    return assemble_prompt_context(
        recommended_modules=all_visual_keys,
        strategy=strategy,
    )