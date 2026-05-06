"""Модуль для парсинга структуры и подробного визуального содержимого PPTX презентаций."""

import logging
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.dml.color import RGBColor

from models.contracts import (
    SlideInfo, 
    PresentationStructure,
    ParsedPresentation,
    ParsedSlide,
    ParsedShape,
    ShapeStyle,
    GroupPosition
)

logger = logging.getLogger(__name__)


def _iter_all_shapes(shapes) -> list:
    """Рекурсивно собирает все элементы (включая сгруппированные) в плоский список."""
    all_shapes = []
    for shape in shapes:
        if shape.shape_type == 6:
            all_shapes.extend(_iter_all_shapes(shape.shapes))
        else:
            all_shapes.append(shape)
    return all_shapes


def parse_pptx(pptx_path: str | Path) -> PresentationStructure:
    """Извлекает базовую структуру, тексты и метаданные слайдов из файла презентации."""
    path = Path(pptx_path)
    logger.info(f"Начало базового парсинга: {path.name}")

    try:
        prs = Presentation(str(path))
    except Exception as e:
        logger.error(f"Не удалось открыть файл {path}: {e}")
        raise RuntimeError(f"Ошибка чтения PPTX: {e}") from e

    try:
        slide_width = prs.slide_width.pt
        slide_height = prs.slide_height.pt
        slides_info: list[SlideInfo] = []

        for idx, slide in enumerate(prs.slides):
            texts = []
            image_count = 0
            shape_count = len(slide.shapes)
            
            for shape in _iter_all_shapes(slide.shapes):
                if getattr(shape, "has_text_frame", False):
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            texts.append(text)
                
                if getattr(shape, "shape_type", None) == 13:
                    image_count += 1

            slide_info = SlideInfo(
                slide_index=idx,
                width=slide_width,
                height=slide_height,
                texts=texts,
                image_count=image_count,
                shape_count=shape_count
            )
            slides_info.append(slide_info)

        result = PresentationStructure(
            filename=path.name,
            slide_count=len(slides_info),
            slides=slides_info
        )
        
        logger.info(f"Распарсено {result.slide_count} слайдов")
        return result

    except Exception as e:
        logger.error(f"Ошибка при разборе содержимого презентации: {e}")
        raise RuntimeError(f"Сбой парсинга слайдов: {e}") from e


def _map_shape_type(shape_type_code: int) -> str:
    """Конвертирует числовой код типа фигуры в строковый идентификатор."""
    mapping = {
        1: "autoshape", 5: "freeform", 6: "group", 13: "picture",
        14: "placeholder", 17: "textbox", 19: "table"
    }
    return mapping.get(shape_type_code, "other")


def _extract_position(shape) -> GroupPosition:
    """Извлекает координаты и размеры фигуры с конвертацией EMU в пиксели."""
    try:
        return GroupPosition(
            x=round(shape.left / 9525),
            y=round(shape.top / 9525),
            w=round(shape.width / 9525),
            h=round(shape.height / 9525)
        )
    except Exception as e:
        logger.warning(f"Ошибка получения координат для фигуры {getattr(shape, 'name', 'unknown')}: {e}")
        return GroupPosition(x=0, y=0, w=0, h=0)


def _extract_text_styles(shape, style: ShapeStyle) -> None:
    """Извлекает стили текста (шрифт, размер, цвет, выравнивание) из первого run."""
    if not getattr(shape, "has_text_frame", False):
        return
        
    try:
        for paragraph in shape.text_frame.paragraphs:
            if paragraph.alignment is not None:
                align_map = {0: "left", 1: "center", 2: "right"}
                style.align = align_map.get(paragraph.alignment, "")
                
            if paragraph.runs:
                run = paragraph.runs[0]
                if run.font.name:
                    style.font_family = run.font.name
                if run.font.size:
                    style.font_size = run.font.size.pt
                if run.font.bold is not None:
                    style.bold = run.font.bold
                if run.font.italic is not None:
                    style.italic = run.font.italic
                try:
                    if run.font.color and hasattr(run.font.color, "rgb") and run.font.color.rgb:
                        style.font_color = f"#{str(run.font.color.rgb)}"
                except Exception as e:
                    logger.warning(f"Не удалось извлечь цвет шрифта: {e}")
                break
    except Exception as e:
        logger.warning(f"Ошибка при обработке текстовых стилей: {e}")


def _extract_fill_lines(shape, style: ShapeStyle) -> None:
    """Извлекает стили заливки и обводки фигуры."""
    try:
        if hasattr(shape, "fill") and shape.fill.type is not None:
            style.fill_color = "#" + str(shape.fill.fore_color.rgb)
    except Exception:
        pass
        
    try:
        if hasattr(shape, "line") and getattr(shape.line, "fill", None) is not None and shape.line.fill.type is not None:
            style.line_color = "#" + str(shape.line.color.rgb)
    except Exception:
        pass


def _extract_table_data(shape) -> list[list[str]] | None:
    """Извлекает текст из всех ячеек таблицы в виде двумерного массива."""
    try:
        return [[cell.text.strip() for cell in row.cells] for row in shape.table.rows]
    except Exception as e:
        logger.warning(f"Ошибка извлечения данных таблицы: {e}")
        return None


def _parse_slide_shapes(slide) -> list[ParsedShape]:
    """Извлекает подробные данные всех фигур на слайде."""
    shapes_data = []
    img_idx = 0
    
    for idx, shape in enumerate(_iter_all_shapes(slide.shapes)):
        s_type = _map_shape_type(getattr(shape, "shape_type", 0))
        if s_type == "picture":
            img_idx += 1
            
        texts = []
        if getattr(shape, "has_text_frame", False):
            texts = [p.text.strip() for p in shape.text_frame.paragraphs if p.text.strip()]
            
        style = ShapeStyle()
        _extract_text_styles(shape, style)
        _extract_fill_lines(shape, style)
        
        shapes_data.append(ParsedShape(
            shape_id=getattr(shape, "shape_id", idx),
            shape_type=s_type,
            name=getattr(shape, "name", ""),
            position=_extract_position(shape),
            rotation=getattr(shape, "rotation", 0.0) or 0.0,
            texts=texts,
            style=style,
            table_data=_extract_table_data(shape) if s_type == "table" else None,
            image_index=img_idx if s_type == "picture" else None
        ))
        
    return shapes_data


def parse_pptx_rich(pptx_path: str | Path) -> ParsedPresentation:
    """Извлекает подробную структуру презентации: позиции, стили, цвета, таблицы."""
    path = Path(pptx_path)
    logger.info(f"Начало rich парсинга: {path.name}")
    
    try:
        prs = Presentation(str(path))
    except Exception as e:
        logger.error(f"Не удалось открыть файл {path}: {e}")
        raise RuntimeError(f"Ошибка чтения PPTX: {e}") from e

    slides_data = []
    for idx, slide in enumerate(prs.slides):
        bg_color = ""
        try:
            if getattr(slide, "background", None) and getattr(slide.background, "fill", None) and slide.background.fill.type is not None:
                if hasattr(slide.background.fill.fore_color, "rgb") and slide.background.fill.fore_color.rgb:
                    bg_color = f"#{str(slide.background.fill.fore_color.rgb)}"
        except Exception:
            pass

        slides_data.append(ParsedSlide(
            slide_index=idx,
            width=prs.slide_width / 9525,
            height=prs.slide_height / 9525,
            background_color=bg_color,
            shapes=_parse_slide_shapes(slide)
        ))

    logger.info(f"Успешно обработано {len(slides_data)} слайдов")
    return ParsedPresentation(filename=path.name, slide_count=len(slides_data), slides=slides_data)


if __name__ == "__main__":
    import sys
    
    test_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    
    try:
        test_result = parse_pptx_rich(test_path)
        for s in test_result.slides:
            logger.info(f"Slide {s.slide_index} | BG: {s.background_color} | Shapes: {len(s.shapes)}")
            for shp in s.shapes:
                txt_preview = shp.texts[0] if shp.texts else ""
                logger.info(f"  [{shp.shape_type}] ID={getattr(shp, 'shape_id', '?')} {shp.name} pos={shp.position} txt='{txt_preview[:30]}'")
        logger.info("Done!")
    except Exception as exc:
        logger.error(f"Сбой выполнения скрипта: {exc}")