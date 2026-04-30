"""Модуль постобработки SVG-файлов: выравнивание по сетке, добавление паддингов и скруглений."""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from core.logger import get_logger

log = get_logger(__name__)

GRID_STEP = 8
MARGIN = 47
SLIDE_W = 1280
SLIDE_H = 720
WORK_X = MARGIN
WORK_Y = MARGIN
WORK_W = SLIDE_W - 2 * MARGIN
WORK_H = SLIDE_H - 2 * MARGIN
CARD_PADDING = 24
CARD_RADIUS = 12
CARD_GAP = 16
TEXT_PADDING = "12"


def snap(value: float) -> float:
    """Округляет значение до ближайшего кратного шагу сетки."""
    return round(value / GRID_STEP) * GRID_STEP


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Ограничивает значение в заданном диапазоне."""
    return max(min_val, min(value, max_val))


def fix_rect(elem: ET.Element) -> None:
    """Исправляет параметры rect: скругления, выравнивание по сетке, удержание в рабочей области."""
    try:
        x = float(elem.get("x", 0))
        y = float(elem.get("y", 0))
        width = float(elem.get("width", 0))
        height = float(elem.get("height", 0))

        if width > 100 and height > 50:
            x = snap(x)
            y = snap(y)
            width = snap(width)
            height = snap(height)
            
            x = clamp(x, MARGIN, SLIDE_W - MARGIN - width)
            y = clamp(y, MARGIN, SLIDE_H - MARGIN - height)

        fill = elem.get("fill", "none")
        if fill != "none" and fill.upper() != "#FFFFFF" and width > 80 and height > 40:
            if elem.get("rx", "0") == "0":
                elem.set("rx", str(CARD_RADIUS))
            if elem.get("ry", "0") == "0":
                elem.set("ry", str(CARD_RADIUS))

        elem.set("x", str(x))
        elem.set("y", str(y))
        elem.set("width", str(width))
        elem.set("height", str(height))
    except ValueError as e:
        log.warning(f"Ошибка преобразования атрибутов rect: {e}")


def fix_text(elem: ET.Element) -> None:
    """Исправляет параметры text: выравнивание по сетке и удержание в рабочей области."""
    try:
        x = float(elem.get("x", 0))
        y = float(elem.get("y", 0))
        
        x = snap(x)
        y = snap(y)
        
        x = clamp(x, MARGIN, SLIDE_W - MARGIN)
        y = clamp(y, MARGIN, SLIDE_H - MARGIN)
        
        elem.set("x", str(x))
        elem.set("y", str(y))
    except ValueError as e:
        log.warning(f"Ошибка преобразования атрибутов text: {e}")


def align_similar_rects(root: ET.Element) -> None:
    """Находит карточки похожего размера и выравнивает их по высоте."""
    try:
        rects = root.findall(".//{http://www.w3.org/2000/svg}rect") + root.findall(".//rect")
        cards = []
        
        for r in rects:
            try:
                w = float(r.get("width", 0))
                h = float(r.get("height", 0))
                if w > 100 and h > 50:
                    cards.append(r)
            except ValueError:
                continue
                
        if len(cards) < 2:
            return
            
        heights = [float(c.get("height", 0)) for c in cards]
        
        if max(heights) - min(heights) < 40:
            target_h = snap(max(heights))
            for c in cards:
                c.set("height", str(target_h))
            log.info(f"  Aligned {len(cards)} cards to height={target_h}")
    except Exception as e:
        log.error(f"Ошибка при выравнивании похожих карточек: {e}")


def fix_svg(svg_path: str | Path) -> Path:
    """Открывает SVG-файл, применяет исправления элементов и сохраняет изменения."""
    try:
        svg_path = Path(svg_path)
        log.info(f"Post-processing: {svg_path.name}")
        
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        tree = ET.parse(str(svg_path))
        root = tree.getroot()
        
        fixed_rects = 0
        fixed_texts = 0
        
        rects = root.findall(".//{http://www.w3.org/2000/svg}rect") + root.findall(".//rect")
        for r in rects:
            fix_rect(r)
            fixed_rects += 1
            
        texts = root.findall(".//{http://www.w3.org/2000/svg}text") + root.findall(".//text")
        for t in texts:
            fix_text(t)
            fixed_texts += 1
            
        align_similar_rects(root)
        
        tree.write(str(svg_path), encoding="unicode", xml_declaration=True)
        log.info(f"  Fixed: {fixed_rects} rects, {fixed_texts} texts")
        
        return svg_path
    except Exception as e:
        log.error(f"Ошибка при исправлении SVG {svg_path}: {e}")
        raise


def fix_all_svgs(svg_dir: str | Path) -> list[Path]:
    """Применяет исправления ко всем SVG-файлам в указанной директории."""
    try:
        svg_dir = Path(svg_dir)
        svg_files = sorted(svg_dir.glob("*.svg"))
        results = []
        
        for svg_file in svg_files:
            fixed_file = fix_svg(svg_file)
            results.append(fixed_file)
            
        return results
    except Exception as e:
        log.error(f"Ошибка при массовой обработке директории {svg_dir}: {e}")
        raise


if __name__ == "__main__":
    try:
        svg_directory = sys.argv[1] if len(sys.argv) > 1 else "temp/svg"
        processed_files = fix_all_svgs(svg_directory)
        print(f"Fixed {len(processed_files)} SVG files")
    except Exception as e:
        log.error(f"Критическая ошибка выполнения: {e}")
        sys.exit(1)