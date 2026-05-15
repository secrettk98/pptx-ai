"""Рендер PNG пустой сетки 12×27 клеток для multimodal-промпта Spatial Architect.

LLM плохо считает пиксели, но хорошо мыслит дискретными клетками. Визуальная
подсказка с пронумерованными колонками и строками помогает Gemini правильно
выбирать row_start_cell/col_start/col_span/height_cells.

Кэширует результат на диск — сетка статична для фиксированных GRID_COLS/GRID_ROWS,
пересчёт не нужен.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.config import (
    GRID_COLS,
    GRID_ROWS,
    WORKING_AREA_W,
    WORKING_AREA_H,
    TEMP_DIR,
)

logger = logging.getLogger(__name__)


# ── Параметры рендера ─────────────────────────────────────────
SCALE: int = 2                                # увеличение от рабочей области
IMG_W: int = WORKING_AREA_W * SCALE           # ширина PNG
IMG_H: int = WORKING_AREA_H * SCALE           # высота PNG
MARGIN_LABEL_TOP: int = 40                    # место под номера колонок
MARGIN_LABEL_LEFT: int = 60                   # место под номера строк
GRID_LINE_WIDTH: int = 1
GRID_LINE_COLOR: tuple[int, int, int] = (200, 200, 200)
GRID_AXIS_COLOR: tuple[int, int, int] = (120, 120, 120)
LABEL_COLOR: tuple[int, int, int] = (80, 80, 80)
BG_COLOR: tuple[int, int, int] = (255, 255, 255)
LABEL_FONT_SIZE: int = 18

# Имя кэш-файла — зависит от размерности сетки
CACHE_FILENAME: str = f"grid_{GRID_COLS}x{GRID_ROWS}_{IMG_W}x{IMG_H}.png"


def _load_font() -> ImageFont.ImageFont:
    """Пытается загрузить системный шрифт, fallback — встроенный."""
    candidates = [
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, LABEL_FONT_SIZE)
        except OSError:
            continue
    logger.warning("Системный шрифт не найден, использую default")
    return ImageFont.load_default()


def _draw_grid(draw: ImageDraw.ImageDraw) -> None:
    """Рисует линии сетки между клетками."""
    total_w = IMG_W - MARGIN_LABEL_LEFT
    total_h = IMG_H - MARGIN_LABEL_TOP
    cell_w = total_w / GRID_COLS
    cell_h = total_h / GRID_ROWS

    # Вертикальные линии колонок
    for col in range(GRID_COLS + 1):
        x = MARGIN_LABEL_LEFT + col * cell_w
        color = GRID_AXIS_COLOR if col in (0, GRID_COLS) else GRID_LINE_COLOR
        draw.line(
            [(x, MARGIN_LABEL_TOP), (x, IMG_H)],
            fill=color, width=GRID_LINE_WIDTH,
        )

    # Горизонтальные линии строк
    for row in range(GRID_ROWS + 1):
        y = MARGIN_LABEL_TOP + row * cell_h
        color = GRID_AXIS_COLOR if row in (0, GRID_ROWS) else GRID_LINE_COLOR
        draw.line(
            [(MARGIN_LABEL_LEFT, y), (IMG_W, y)],
            fill=color, width=GRID_LINE_WIDTH,
        )


def _draw_labels(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont) -> None:
    """Подписывает колонки сверху и строки слева."""
    total_w = IMG_W - MARGIN_LABEL_LEFT
    total_h = IMG_H - MARGIN_LABEL_TOP
    cell_w = total_w / GRID_COLS
    cell_h = total_h / GRID_ROWS

    # Номера колонок (0..GRID_COLS-1) по центру каждой клетки
    for col in range(GRID_COLS):
        cx = MARGIN_LABEL_LEFT + col * cell_w + cell_w / 2
        cy = MARGIN_LABEL_TOP / 2
        text = str(col)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (cx - tw / 2, cy - th / 2),
            text, fill=LABEL_COLOR, font=font,
        )

    # Номера строк (0..GRID_ROWS-1) по центру каждой клетки
    for row in range(GRID_ROWS):
        cx = MARGIN_LABEL_LEFT / 2
        cy = MARGIN_LABEL_TOP + row * cell_h + cell_h / 2
        text = str(row)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (cx - tw / 2, cy - th / 2),
            text, fill=LABEL_COLOR, font=font,
        )


def _render_grid_image() -> Image.Image:
    """Создаёт PIL-изображение с пустой сеткой и подписями."""
    img = Image.new("RGB", (IMG_W, IMG_H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = _load_font()
    _draw_grid(draw)
    _draw_labels(draw, font)
    return img


def get_grid_image_path() -> Path:
    """Возвращает путь к PNG сетки. Рендерит и кэширует при первом вызове.

    Кэш-файл лежит в TEMP_DIR. Имя содержит размерность сетки и размер картинки,
    поэтому при изменении констант в config.py старый кэш не используется.
    """
    cache_path = TEMP_DIR / CACHE_FILENAME
    if cache_path.exists():
        logger.debug(f"Использую кэшированную сетку: {cache_path}")
        return cache_path

    try:
        img = _render_grid_image()
        img.save(cache_path, format="PNG", optimize=True)
        logger.info(
            f"Сетка {GRID_COLS}×{GRID_ROWS} отрендерена в {cache_path} "
            f"({IMG_W}×{IMG_H} px)"
        )
        return cache_path
    except (OSError, ValueError) as e:
        logger.error(f"Не удалось отрендерить сетку: {e}")
        raise


def get_grid_image_bytes() -> bytes:
    """Возвращает PNG как bytes (для прямой передачи в multimodal API)."""
    path = get_grid_image_path()
    try:
        return path.read_bytes()
    except OSError as e:
        logger.error(f"Не удалось прочитать PNG сетки {path}: {e}")
        raise