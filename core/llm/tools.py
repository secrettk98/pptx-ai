"""
Реестр tools для Gemini function calling.

Содержит декларации функций (schema) и Python-обработчики.
Используется Semantic Editor для точного измерения текста и таблиц
в клетках сетки 12×27 — LLM делегирует измерения Python, не считает сама.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from google.genai import types

from core.utils.text_metrics import measure_text_in_cells, measure_table_in_cells

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Tool: measure_texts_batch
# ─────────────────────────────────────────────────────────────

MEASURE_TEXTS_BATCH_DECL = types.FunctionDeclaration(
    name="measure_texts_batch",
    description=(
        "Точно измеряет высоту текстовых блоков и таблиц в клетках сетки 12×27. "
        "Принимает батч элементов — вызывай ОДИН раз на весь слайд, не по одному. "
        "Для kind='text' заполняй поле text. Для kind='table' заполняй table_data "
        "(массив строк, первая строка — заголовок). Возвращает height_cells для каждого block_id."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "items": types.Schema(
                type=types.Type.ARRAY,
                description="Список блоков для измерения",
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "block_id": types.Schema(
                            type=types.Type.STRING,
                            description="Уникальный ID блока",
                        ),
                        "kind": types.Schema(
                            type=types.Type.STRING,
                            description="Тип контента: 'text' или 'table'",
                            enum=["text", "table"],
                        ),
                        "width_cols": types.Schema(
                            type=types.Type.INTEGER,
                            description="Ширина блока в колонках сетки (1-12)",
                        ),
                        "text": types.Schema(
                            type=types.Type.STRING,
                            description="Текст блока (для kind='text')",
                        ),
                        "table_data": types.Schema(
                            type=types.Type.ARRAY,
                            description="Данные таблицы как массив строк (для kind='table')",
                            items=types.Schema(
                                type=types.Type.ARRAY,
                                items=types.Schema(type=types.Type.STRING),
                            ),
                        ),
                        "style": types.Schema(
                            type=types.Type.OBJECT,
                            description="Стиль шрифта",
                            properties={
                                "size_pt": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Размер шрифта в пунктах",
                                ),
                                "bold": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Жирность",
                                ),
                                "line_factor": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Межстрочный интервал (опц., дефолт 1.35)",
                                ),
                            },
                            required=["size_pt"],
                        ),
                    },
                    required=["block_id", "kind", "width_cols", "style"],
                ),
            ),
        },
        required=["items"],
    ),
)


def _handle_measure_texts_batch(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Обработчик measure_texts_batch — возвращает {block_id: height_cells}."""
    result: dict[str, int] = {}
    for item in items:
        block_id = item.get("block_id")
        if not block_id:
            logger.warning(f"Пропуск item без block_id: {item}")
            continue
        try:
            kind = item.get("kind", "text")
            width_cols = int(item["width_cols"])
            style = item.get("style", {})
            size_pt = float(style.get("size_pt", 12))
            bold = bool(style.get("bold", False))
            line_factor = float(style.get("line_factor", 1.35))

            if kind == "text":
                text = item.get("text", "") or ""
                height = measure_text_in_cells(text, width_cols, size_pt, bold, line_factor)
            elif kind == "table":
                table_data = item.get("table_data") or []
                height = measure_table_in_cells(table_data, width_cols, size_pt, True, line_factor)
            else:
                logger.warning(f"Неизвестный kind '{kind}' для {block_id}, пропуск")
                continue

            result[block_id] = height
            logger.info(f"  [{block_id}] kind={kind}, width_cols={width_cols} → {height} клеток")
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Ошибка измерения {block_id}: {e}")
            result[block_id] = 0
    return {"heights": result}


# ─────────────────────────────────────────────────────────────
# Экспорт
# ─────────────────────────────────────────────────────────────

TOOL_DECLARATIONS: list[types.FunctionDeclaration] = [
    MEASURE_TEXTS_BATCH_DECL,
]

TOOL_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "measure_texts_batch": _handle_measure_texts_batch,
}