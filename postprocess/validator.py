"""Слой 2.5 — Python Validator для LayoutPlanV5.

Проверяет план в клеточной сетке 12×27 на overflow / overlap / negative coords.
Считает penalty score, формирует текстовый feedback для Spatial Architect,
дампит каждую попытку на диск.

LLM не калькулятор — все проверки делает Python в матрице клеток.

Контракт:
    validate(plan, slide_index, attempt) → ValidationResult
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from core.config import (
    GRID_COLS,
    GRID_ROWS,
    DEBUG_DIR,
    OVERFLOW_PENALTY_PER_CELL,
    OVERLAP_PENALTY,
    NEGATIVE_COORD_PENALTY,
)
from models.contracts import LayoutPlanV5, GridRow, GridBlock

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
#  МОДЕЛЬ РЕЗУЛЬТАТА
# ════════════════════════════════════════════════════════════

class ValidationIssue(BaseModel):
    """Одна найденная проблема в плане."""
    kind: str = Field(description="overflow_v / overflow_h / overlap / negative")
    block_id: Optional[str] = None
    row_id: Optional[str] = None
    message: str
    cells_affected: int = 0


class ValidationResult(BaseModel):
    """Результат валидации одного плана."""
    is_valid: bool
    penalty: float = 0.0
    issues: list[ValidationIssue] = Field(default_factory=list)
    feedback: str = Field(default="", description="Текст для отправки Architect-у")
    occupancy_summary: str = Field(default="", description="Краткая карта занятости")
    changed_col_spans: dict[str, int] = Field(
        default_factory=dict,
        description="block_id → новый col_span (если отличается от proposed)",
    )


# ════════════════════════════════════════════════════════════
#  ПРОВЕРКИ
# ════════════════════════════════════════════════════════════

def _check_negative_coords(plan: LayoutPlanV5) -> list[ValidationIssue]:
    """Отрицательные row_start_cell / col_start."""
    issues: list[ValidationIssue] = []
    for row in plan.rows:
        if row.row_start_cell < 0:
            issues.append(ValidationIssue(
                kind="negative",
                row_id=row.row_id,
                message=(
                    f"Ряд {row.row_id}: row_start_cell={row.row_start_cell} < 0"
                ),
                cells_affected=abs(row.row_start_cell),
            ))
        for blk in row.blocks:
            if blk.col_start < 0:
                issues.append(ValidationIssue(
                    kind="negative",
                    block_id=blk.block_id,
                    row_id=row.row_id,
                    message=(
                        f"Блок {blk.block_id}: col_start={blk.col_start} < 0"
                    ),
                    cells_affected=abs(blk.col_start),
                ))
            if blk.row_start_cell < 0:
                issues.append(ValidationIssue(
                    kind="negative",
                    block_id=blk.block_id,
                    row_id=row.row_id,
                    message=(
                        f"Блок {blk.block_id}: row_start_cell="
                        f"{blk.row_start_cell} < 0"
                    ),
                    cells_affected=abs(blk.row_start_cell),
                ))
    return issues


def _check_horizontal_overflow(plan: LayoutPlanV5) -> list[ValidationIssue]:
    """col_start + col_span > GRID_COLS."""
    issues: list[ValidationIssue] = []
    for row in plan.rows:
        for blk in row.blocks:
            right_edge = blk.col_start + blk.col_span
            if right_edge > GRID_COLS:
                over = right_edge - GRID_COLS
                issues.append(ValidationIssue(
                    kind="overflow_h",
                    block_id=blk.block_id,
                    row_id=row.row_id,
                    message=(
                        f"Блок {blk.block_id}: col_start={blk.col_start} + "
                        f"col_span={blk.col_span} = {right_edge}, "
                        f"превышает {GRID_COLS} на {over} клеток"
                    ),
                    cells_affected=over,
                ))
    return issues


def _check_vertical_overflow(plan: LayoutPlanV5) -> list[ValidationIssue]:
    """Максимальная нижняя кромка по всем блокам > GRID_ROWS."""
    issues: list[ValidationIssue] = []
    max_bottom = 0
    for row in plan.rows:
        for blk in row.blocks:
            bottom = blk.row_start_cell + blk.height_cells
            if bottom > max_bottom:
                max_bottom = bottom
    if max_bottom > GRID_ROWS:
        over = max_bottom - GRID_ROWS
        issues.append(ValidationIssue(
            kind="overflow_v",
            message=(
                f"Суммарная высота контента {max_bottom} клеток "
                f"превышает {GRID_ROWS} на {over}"
            ),
            cells_affected=over,
        ))
    return issues


def _build_occupancy_matrix(plan: LayoutPlanV5) -> list[list[Optional[str]]]:
    """Матрица [GRID_ROWS × GRID_COLS] из block_id или None.

    Координаты вне сетки игнорируются (их ловят другие проверки).
    """
    matrix: list[list[Optional[str]]] = [
        [None] * GRID_COLS for _ in range(GRID_ROWS)
    ]
    overlaps: list[tuple[str, str, int, int]] = []

    for row in plan.rows:
        for blk in row.blocks:
            r0 = blk.row_start_cell
            r1 = blk.row_start_cell + blk.height_cells
            c0 = blk.col_start
            c1 = blk.col_start + blk.col_span

            for r in range(max(0, r0), min(GRID_ROWS, r1)):
                for c in range(max(0, c0), min(GRID_COLS, c1)):
                    occupant = matrix[r][c]
                    if occupant is not None and occupant != blk.block_id:
                        overlaps.append((occupant, blk.block_id, r, c))
                    else:
                        matrix[r][c] = blk.block_id

    # Сохраняем overlaps как атрибут (без модификации сигнатуры)
    setattr(_build_occupancy_matrix, "_last_overlaps", overlaps)
    return matrix


def _check_overlaps(plan: LayoutPlanV5) -> list[ValidationIssue]:
    """Пересечения блоков в матрице клеток."""
    _build_occupancy_matrix(plan)
    overlaps = getattr(_build_occupancy_matrix, "_last_overlaps", [])
    issues: list[ValidationIssue] = []

    # Группируем по парам (block_a, block_b)
    pair_cells: dict[tuple[str, str], int] = {}
    for a, b, _r, _c in overlaps:
        key = tuple(sorted([a, b]))
        pair_cells[key] = pair_cells.get(key, 0) + 1

    for (a, b), n_cells in pair_cells.items():
        issues.append(ValidationIssue(
            kind="overlap",
            block_id=f"{a}+{b}",
            message=(
                f"Блоки {a} и {b} пересекаются на {n_cells} клеток"
            ),
            cells_affected=n_cells,
        ))
    return issues


# ════════════════════════════════════════════════════════════
#  СРАВНЕНИЕ С PROPOSED_COL_SPAN
# ════════════════════════════════════════════════════════════

def _detect_changed_spans(
    plan: LayoutPlanV5,
    proposed_spans: dict[str, int],
) -> dict[str, int]:
    """Возвращает {block_id: new_col_span} для блоков, чей col_span изменился.

    proposed_spans берётся из SemanticBlock.proposed_col_span.
    Architect мог пересмотреть ширину — тогда height_cells нужно пере-измерить.
    """
    changed: dict[str, int] = {}
    for row in plan.rows:
        for blk in row.blocks:
            proposed = proposed_spans.get(blk.block_id)
            if proposed is not None and proposed != blk.col_span:
                changed[blk.block_id] = blk.col_span
    return changed


# ════════════════════════════════════════════════════════════
#  PENALTY
# ════════════════════════════════════════════════════════════

def _compute_penalty(issues: list[ValidationIssue]) -> float:
    """Суммарная оценка по весам из config."""
    score = 0.0
    for iss in issues:
        if iss.kind in ("overflow_v", "overflow_h"):
            score += iss.cells_affected * OVERFLOW_PENALTY_PER_CELL
        elif iss.kind == "overlap":
            score += iss.cells_affected * OVERLAP_PENALTY
        elif iss.kind == "negative":
            score += iss.cells_affected * NEGATIVE_COORD_PENALTY
    return round(score, 2)


# ════════════════════════════════════════════════════════════
#  FEEDBACK ДЛЯ ARCHITECT
# ════════════════════════════════════════════════════════════

def _build_feedback(
    issues: list[ValidationIssue],
    penalty: float,
) -> str:
    """Человекочитаемый feedback для следующей итерации Architect."""
    if not issues:
        return ""

    lines: list[str] = [
        f"Предыдущая попытка получила penalty={penalty}.",
        "Найденные проблемы:",
    ]
    for iss in issues:
        lines.append(f"  - [{iss.kind}] {iss.message}")
    lines.append("")
    lines.append("Исправь план так, чтобы:")
    lines.append(f"  1. Сумма height_cells по вертикали ≤ {GRID_ROWS} клеток")
    lines.append(f"  2. col_start + col_span ≤ {GRID_COLS} для каждого блока")
    lines.append("  3. Блоки не пересекаются в матрице клеток")
    lines.append("  4. Все координаты неотрицательные")
    return "\n".join(lines)


def _build_occupancy_summary(plan: LayoutPlanV5) -> str:
    """Короткая ASCII-карта занятости (для логов и дампа)."""
    matrix = _build_occupancy_matrix(plan)
    # Сжимаем block_id → одиночный символ
    ids: list[str] = []
    for row in matrix:
        for cell in row:
            if cell is not None and cell not in ids:
                ids.append(cell)
    symbol_map = {bid: chr(ord("A") + i % 26) for i, bid in enumerate(ids)}

    lines: list[str] = []
    for r in range(GRID_ROWS):
        line_chars = []
        for c in range(GRID_COLS):
            cell = matrix[r][c]
            line_chars.append(symbol_map[cell] if cell else ".")
        lines.append("".join(line_chars))
    legend = ", ".join(f"{s}={bid}" for bid, s in symbol_map.items())
    return "\n".join(lines) + "\n\nLegend: " + legend


# ════════════════════════════════════════════════════════════
#  ДАМП ПОПЫТОК
# ════════════════════════════════════════════════════════════

def _slide_debug_dir(slide_index: int) -> Path:
    """Папка для дампов одного слайда."""
    path = DEBUG_DIR / f"slide_{slide_index:03d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _dump_attempt(
    plan: LayoutPlanV5,
    result: ValidationResult,
    slide_index: int,
    attempt: int,
) -> None:
    """Сохраняет план + результат валидации в JSON."""
    out_dir = _slide_debug_dir(slide_index)
    payload = {
        "attempt": attempt,
        "plan": plan.model_dump(),
        "result": result.model_dump(),
    }
    try:
        target = out_dir / f"attempt_{attempt:02d}.json"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug(f"Дамп попытки сохранён: {target}")
    except OSError as e:
        logger.error(f"Не удалось записать дамп attempt_{attempt}: {e}")


def dump_chosen(
    plan: LayoutPlanV5,
    result: ValidationResult,
    slide_index: int,
) -> None:
    """Сохраняет финальный (выбранный) план — вызывается из orchestrator."""
    out_dir = _slide_debug_dir(slide_index)
    payload = {
        "plan": plan.model_dump(),
        "result": result.model_dump(),
    }
    try:
        target = out_dir / "chosen.json"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Финальный план слайда {slide_index} → {target}")
    except OSError as e:
        logger.error(f"Не удалось записать chosen.json: {e}")


# ════════════════════════════════════════════════════════════
#  ПУБЛИЧНЫЙ API
# ════════════════════════════════════════════════════════════

def validate(
    plan: LayoutPlanV5,
    slide_index: int,
    attempt: int,
    proposed_spans: Optional[dict[str, int]] = None,
) -> ValidationResult:
    """Главный вход: валидирует план и возвращает результат с feedback.

    Args:
        plan: LayoutPlanV5 от Spatial Architect (уже после Enrich)
        slide_index: индекс слайда для имени дампа
        attempt: номер попытки (0, 1, 2...)
        proposed_spans: {block_id: proposed_col_span} из SemanticSlide —
            нужен, чтобы понять, изменил ли Architect ширины блоков
            (тогда orchestrator пере-меряет height_cells через tool)

    Returns:
        ValidationResult с penalty, issues, feedback и changed_col_spans.
    """
    issues: list[ValidationIssue] = []
    issues.extend(_check_negative_coords(plan))
    issues.extend(_check_horizontal_overflow(plan))
    issues.extend(_check_vertical_overflow(plan))
    issues.extend(_check_overlaps(plan))

    penalty = _compute_penalty(issues)
    is_valid = len(issues) == 0
    feedback = _build_feedback(issues, penalty) if not is_valid else ""
    occupancy = _build_occupancy_summary(plan)

    changed: dict[str, int] = {}
    if proposed_spans:
        changed = _detect_changed_spans(plan, proposed_spans)

    result = ValidationResult(
        is_valid=is_valid,
        penalty=penalty,
        issues=issues,
        feedback=feedback,
        occupancy_summary=occupancy,
        changed_col_spans=changed,
    )

    _dump_attempt(plan, result, slide_index, attempt)

    logger.info(
        f"Validator: слайд {slide_index} попытка {attempt} → "
        f"valid={is_valid} penalty={penalty} issues={len(issues)} "
        f"changed_spans={len(changed)}"
    )
    return result