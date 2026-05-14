"""
Spatial Architect (Слой 1) — принимает SemanticSlide + design_context,
мыслит в 12-колоночной сетке и возвращает LayoutPlanV5.
Модель: Gemini 2.5 Flash.
"""

import json
import logging
import re
from pathlib import Path

from core.config import MODEL_DESIGNER, PROMPTS_DIR
from core.llm.client import call_llm
from core.llm.normalize import normalize_for_model
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


def _build_user_message(
    semantic_slide: SemanticSlide,
    strategy: PresentationStrategy,
    design_context: str,
) -> str:
    """Формирует user-сообщение для Architect."""
    blocks_summary = [
        {
            "block_id": b.block_id,
            "semantic_type": b.semantic_type,
            "visual_subtype": b.visual_subtype,
            "line_budget": b.line_budget,
            "content_keys": list(b.content.keys()),
        }
        for b in semantic_slide.blocks
    ]
    return (
        f"# SLIDE {semantic_slide.slide_index}\n\n"
        f"## Strategy\n"
        f"header_type={strategy.header_type}, style_mode={strategy.style_mode}, "
        f"accent={strategy.accent_color}, mode={strategy.presentation_mode}\n\n"
        f"## Semantic blocks ({semantic_slide.total_lines} lines total)\n"
        f"{json.dumps(blocks_summary, ensure_ascii=False, indent=2)}\n\n"
        f"## Design context\n{design_context}"
    )


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
                    b_norm["block_id"] = f"sb{bi}"
                blocks.append(GridBlock(**b_norm))
            except Exception as e:
                logger.warning(
                    f"Слайд {slide_index}, ряд {ri}, блок {bi} пропущен: {e}"
                )

        # Проверка суммы col_span
        col_sum = sum(b.col_span for b in blocks)
        if col_sum != 12:
            logger.warning(
                f"Слайд {slide_index}, ряд {row_id}: "
                f"col_span сумма = {col_sum} (ожидалось 12)"
            )

        rows.append(
            GridRow(
                row_id=row_id,
                blocks=blocks,
                row_lines=row_data.get("row_lines", 0),
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

    total_lines = data_norm.get("total_lines") or sum(r.row_lines for r in rows)

    return LayoutPlanV5(
        slide_index=slide_index,
        slide_role=data_norm.get("slide_role", "content"),
        header_type=data_norm.get("header_type", "B"),
        style_mode=data_norm.get("style_mode", "soft"),
        needs_footer=data_norm.get("needs_footer", False),
        composition_schema=data_norm.get("composition_schema", "A"),
        rows=rows,
        total_lines=total_lines,
        design_notes=data_norm.get("design_notes", ""),
    )


def design_slide(
    semantic_slide: SemanticSlide,
    strategy: PresentationStrategy,
    design_context: str,
    slide_index: int,
) -> LayoutPlanV5:
    """
    Слой 1: превращает SemanticSlide в LayoutPlanV5.

    Args:
        semantic_slide: выход Semantic Editor
        strategy:       стратегия презентации
        design_context: строка из Prompt Assembler
        slide_index:    индекс слайда

    Returns:
        LayoutPlanV5 с list[GridRow]
    """
    logger.info(f"SpatialArchitect: слайд {slide_index}")

    system_prompt = _load_system_prompt()
    user_msg = _build_user_message(semantic_slide, strategy, design_context)

    try:
        raw = call_llm(
            prompt=user_msg,
            model_name=MODEL_DESIGNER,
            image_path=None,
            json_mode=False,  # ответ содержит <thinking>, потом JSON
            system_instruction=system_prompt,
        )
    except Exception as e:
        logger.error(f"Слайд {slide_index}: LLM Architect упал: {e}")
        raise

    result = _parse_response(raw, slide_index)
    logger.info(
        f"SpatialArchitect слайд {slide_index}: "
        f"{len(result.rows)} рядов, role={result.slide_role}, "
        f"lines={result.total_lines}"
    )
    return result