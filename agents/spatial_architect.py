"""
Spatial Architect (Слой 1) — финализирует layout в клеточной сетке 12×27.

Получает SemanticSlide с точными height_cells (измеренными Semantic через tool),
дизайн-контекст и PNG пустой сетки 12×27. Возвращает LayoutPlanV5 с явными
координатами row_start_cell / col_start / col_span / height_cells для каждого блока.

При retry получает feedback от Validator с описанием проблем предыдущей попытки.
Модель: Gemini 2.5 Pro (multimodal).
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from core.config import MODEL_DESIGNER, PROMPTS_DIR
from core.llm.client import call_llm
from core.llm.normalize import normalize_for_model
from core.utils.grid_visualizer import get_grid_image_path
from models.contracts import (
    GridBlock,
    GridRow,
    LayoutPlanV5,
    PresentationStrategy,
    SemanticSlide,
)

logger = logging.getLogger(__name__)

PROMPT_FILE: Path = PROMPTS_DIR / "spatial_architect.md"


def _load_system_prompt() -> str:
    """Читает системный промпт Spatial Architect."""
    try:
        return PROMPT_FILE.read_text(encoding="utf-8")
    except OSError as e:
        logger.error(f"Не удалось прочитать промпт {PROMPT_FILE}: {e}")
        raise


def _build_blocks_summary(semantic_slide: SemanticSlide) -> list[dict]:
    """Сводка блоков для LLM — без content, только метаданные и размеры."""
    return [
        {
            "block_id": b.block_id,
            "semantic_type": b.semantic_type,
            "visual_subtype": b.visual_subtype,
            "priority": b.priority,
            "proposed_col_span": b.proposed_col_span,
            "height_cells": b.height_cells,
        }
        for b in semantic_slide.blocks
    ]


def _build_user_message(
    semantic_slide: SemanticSlide,
    strategy: PresentationStrategy,
    design_context: str,
    feedback: Optional[str],
) -> str:
    """Формирует user-сообщение для Architect."""
    blocks_summary = _build_blocks_summary(semantic_slide)
    parts: list[str] = [
        f"# SLIDE {semantic_slide.slide_index}",
        "",
        "## Strategy",
        (
            f"header_type={strategy.header_type}, "
            f"style_mode={strategy.style_mode}, "
            f"accent={strategy.accent_color}, "
            f"mode={strategy.presentation_mode}"
        ),
        "",
        f"## Semantic blocks (total_height_cells={semantic_slide.total_height_cells})",
        json.dumps(blocks_summary, ensure_ascii=False, indent=2),
        "",
        "## Design context",
        design_context,
    ]
    if feedback:
        parts.extend([
            "",
            "## Validator feedback (previous attempt failed)",
            feedback,
        ])
    return "\n".join(parts)


def _strip_thinking(raw: str) -> str:
    """Убирает <thinking> блок — оставляет только JSON."""
    clean = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    clean = clean.replace("```json", "").replace("```", "").strip()
    return clean


def _parse_rows(rows_raw: list[dict], slide_index: int) -> list[GridRow]:
    """Конвертирует сырой список рядов в list[GridRow]."""
    rows: list[GridRow] = []
    for ri, row_data in enumerate(rows_raw):
        row_id = row_data.get("row_id") or f"r{ri}"
        blocks_raw: list[dict] = row_data.get("blocks", [])
        blocks: list[GridBlock] = []

        for bi, b in enumerate(blocks_raw):
            try:
                b_norm = normalize_for_model(b, GridBlock)
                if not b_norm.get("block_id"):
                    logger.warning(
                        f"Слайд {slide_index}, ряд {ri}, блок {bi}: "
                        f"пустой block_id — пропуск"
                    )
                    continue
                blocks.append(GridBlock(**b_norm))
            except Exception as e:
                logger.warning(
                    f"Слайд {slide_index}, ряд {ri}, блок {bi} пропущен: {e}"
                )

        col_sum = sum(b.col_span for b in blocks)
        if col_sum != 12:
            logger.warning(
                f"Слайд {slide_index}, ряд {row_id}: "
                f"сумма col_span = {col_sum} (ожидалось 12)"
            )

        row_height = (
            max((b.height_cells for b in blocks), default=0) if blocks else 0
        )
        row_start = row_data.get("row_start_cell", 0)

        rows.append(
            GridRow(
                row_id=row_id,
                row_start_cell=row_start,
                height_cells=row_data.get("height_cells", row_height),
                blocks=blocks,
            )
        )
    return rows


def _parse_response(raw: str, slide_index: int) -> LayoutPlanV5:
    """Парсит JSON-ответ LLM → LayoutPlanV5."""
    clean = _strip_thinking(raw)
    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(
            f"Слайд {slide_index}: JSON Architect не распознан: {e}\n"
            f"Raw: {clean[:300]}"
        )
        raise

    rows = _parse_rows(data.pop("rows", []), slide_index)
    data_norm = normalize_for_model(data, LayoutPlanV5)

    total_height = data_norm.get("total_height_cells") or sum(
        r.height_cells for r in rows
    )

    return LayoutPlanV5(
        slide_index=slide_index,
        slide_role=data_norm.get("slide_role", "content"),
        header_type=data_norm.get("header_type", "B"),
        style_mode=data_norm.get("style_mode", "soft"),
        needs_footer=data_norm.get("needs_footer", False),
        composition_schema=data_norm.get("composition_schema", "A"),
        rows=rows,
        total_height_cells=total_height,
        design_notes=data_norm.get("design_notes", ""),
    )


def design_slide(
    semantic_slide: SemanticSlide,
    strategy: PresentationStrategy,
    design_context: str,
    slide_index: int,
    feedback: Optional[str] = None,
) -> LayoutPlanV5:
    """
    Слой 1: финализирует layout в клеточной сетке 12×27.

    Args:
        semantic_slide: выход Semantic Editor (с точными height_cells)
        strategy:       стратегия презентации
        design_context: строка от Prompt Assembler
        slide_index:    индекс слайда
        feedback:       если retry — текст от Validator с описанием проблем

    Returns:
        LayoutPlanV5 с list[GridRow], каждый GridBlock имеет
        row_start_cell, col_start, col_span, height_cells.
    """
    logger.info(
        f"SpatialArchitect: слайд {slide_index}"
        + (" (retry с feedback)" if feedback else "")
    )

    system_prompt = _load_system_prompt()
    user_msg = _build_user_message(
        semantic_slide, strategy, design_context, feedback
    )

    try:
        grid_image_path = get_grid_image_path()
    except (OSError, ValueError) as e:
        logger.error(f"Не удалось получить PNG сетки: {e}")
        raise

    try:
        raw = call_llm(
            prompt=user_msg,
            model_name=MODEL_DESIGNER,
            image_path=str(grid_image_path),
            json_mode=False,
            system_instruction=system_prompt,
        )
    except Exception as e:
        logger.error(f"Слайд {slide_index}: LLM Architect упал: {e}")
        raise

    result = _parse_response(raw, slide_index)
    logger.info(
        f"SpatialArchitect слайд {slide_index}: "
        f"{len(result.rows)} рядов, role={result.slide_role}, "
        f"total_height_cells={result.total_height_cells}"
    )
    return result