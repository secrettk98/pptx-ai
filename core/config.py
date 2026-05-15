"""
Централизованные настройки и константы проекта PPTX-AI.

Содержит пути, API ключи, модели LLM, параметры дизайн-системы
и константы клеточной сетки 12×27 для layout v5.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Пути проекта
# ─────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
TEMP_DIR: Path = PROJECT_ROOT / "temp"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"
DEBUG_DIR: Path = OUTPUT_DIR / "debug"
PROMPTS_DIR: Path = PROJECT_ROOT / "prompts"
CONFIG_DIR: Path = PROJECT_ROOT / "config"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
PROJECTS_DIR: Path = PROJECT_ROOT / "projects"

# ─────────────────────────────────────────────────────────────
# API ключи (из .env)
# ─────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MAPBOX_ACCESS_TOKEN: str = os.getenv("MAPBOX_ACCESS_TOKEN", "")

# ─────────────────────────────────────────────────────────────
# Модели LLM
# ─────────────────────────────────────────────────────────────
MODEL_VISION: str = "gemini-2.5-flash"
MODEL_CLASSIFIER: str = "gemini-2.5-flash"
MODEL_BRAIN: str = "gemini-2.5-pro"
MODEL_DESIGNER: str = "gemini-2.5-pro"
MODEL_INSPECTOR: str = "gemini-2.5-flash"
MODEL_CHEAP: str = "gemini-2.5-flash-lite"

# ─────────────────────────────────────────────────────────────
# Лимиты LLM
# ─────────────────────────────────────────────────────────────
LLM_TIMEOUT: int = 60
LLM_MAX_RETRIES: int = 3
MAX_INSPECTOR_RETRIES: int = 2
MAX_VALIDATOR_RETRIES: int = 2
MAX_TOOL_CALLS_PER_SLIDE: int = 5

# ─────────────────────────────────────────────────────────────
# Design System — размеры слайда
# ─────────────────────────────────────────────────────────────
SLIDE_WIDTH: int = 1280
SLIDE_HEIGHT: int = 720
SLIDE_MARGIN_X: int = 42                 # горизонтальный отступ (лево/право)
SLIDE_MARGIN_Y: int = 22                 # вертикальный отступ (верх/низ)
WORKING_AREA_W: int = 1196               # 1280 - 2*42
WORKING_AREA_H: int = 676                # 720 - 2*22

# ─────────────────────────────────────────────────────────────
# Клеточная сетка 12×27 (layout v5)
# ─────────────────────────────────────────────────────────────
GRID_COLS: int = 12
GRID_ROWS: int = 27
CELL_WIDTH: float = WORKING_AREA_W / GRID_COLS      # ≈ 99.67 px
CELL_HEIGHT: float = WORKING_AREA_H / GRID_ROWS     # ≈ 25.04 px
ROW_GAP_CELLS: int = 1                              # фиксированный gap между рядами (в клетках)

# ─────────────────────────────────────────────────────────────
# Validator — веса penalty
# ─────────────────────────────────────────────────────────────
OVERFLOW_PENALTY_PER_CELL: float = 1.0
OVERLAP_PENALTY: float = 100.0
NEGATIVE_COORD_PENALTY: float = 50.0

# ─────────────────────────────────────────────────────────────
# Типографика
# ─────────────────────────────────────────────────────────────
COLOR_ACCENT_DEFAULT: str = "#0066CC"
FONT_FAMILY: str = "Google Sans"

# ─────────────────────────────────────────────────────────────
# DEPRECATED — старая колоночная система (удалить на Шаге 3)
# ─────────────────────────────────────────────────────────────
GRID_COLUMNS: int = 12                   # alias к GRID_COLS
COLUMN_WIDTH: int = 72                   # старая ширина колонки с гаттерами
GUTTER: int = 30                         # старый зазор между колонками

# ─────────────────────────────────────────────────────────────
# Создание необходимых директорий
# ─────────────────────────────────────────────────────────────
try:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Директории temp/output/debug успешно инициализированы")
except OSError as e:
    logger.error(f"Не удалось создать базовые директории: {e}")
    raise