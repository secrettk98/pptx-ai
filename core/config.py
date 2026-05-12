"""Централизованные настройки и константы проекта PPTX-AI."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Базовые пути проекта
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Папки
TEMP_DIR: Path = PROJECT_ROOT / "temp"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"
PROMPTS_DIR: Path = PROJECT_ROOT / "prompts"
CONFIG_DIR: Path = PROJECT_ROOT / "config"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
PROJECTS_DIR: Path = PROJECT_ROOT / "projects"

# API ключи (из переменных окружения)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MAPBOX_ACCESS_TOKEN: str = os.getenv("MAPBOX_ACCESS_TOKEN", "")

# Модели AI
MODEL_VISION: str = "gemini-2.5-flash"
MODEL_CLASSIFIER: str = "gemini-2.5-flash"
MODEL_BRAIN: str = "gemini-2.5-pro"
MODEL_DESIGNER: str = "gemini-2.5-pro"
MODEL_INSPECTOR: str = "gemini-2.5-flash"
MODEL_CHEAP: str = "gemini-2.5-flash-lite"

# Лимиты
MAX_INSPECTOR_RETRIES: int = 2
LLM_TIMEOUT: int = 60
LLM_MAX_RETRIES: int = 3

# Design System
SLIDE_WIDTH: int = 1280
SLIDE_HEIGHT: int = 720
SLIDE_MARGIN: int = 47
COLOR_ACCENT_DEFAULT: str = "#0066CC"
FONT_FAMILY: str = "Google Sans"

# Создание необходимых директорий
try:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Директории temp и output успешно инициализированы")
except OSError as e:
    logger.error(f"Не удалось создать базовые директории: {e}")
    raise