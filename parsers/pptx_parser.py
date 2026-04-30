"""Модуль для парсинга структуры и содержимого PPTX презентаций."""

from pathlib import Path
from pptx import Presentation
from pptx.util import Emu
from models.contracts import SlideInfo, PresentationStructure
from core.logger import get_logger

log = get_logger(__name__)


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
    """Извлекает структуру, тексты и метаданные слайдов из файла презентации."""
    path = Path(pptx_path)
    log.info(f"Parsing: {path.name}")

    try:
        prs = Presentation(str(path))
    except Exception as e:
        log.error(f"Не удалось открыть файл {path}: {e}")
        raise RuntimeError(f"Ошибка чтения PPTX: {e}") from e

    try:
        slide_width = prs.slide_width.pt
        slide_height = prs.slide_height.pt
        slides_info: list[SlideInfo] = []

        for idx, slide in enumerate(prs.slides):
            texts: list[str] = []
            image_count = 0
            
            flat_shapes = _iter_all_shapes(slide.shapes)
            shape_count = len(flat_shapes)

            for shape in flat_shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            texts.append(text)
                
                if shape.shape_type == 13:
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
        
        log.info(f"Parsed {result.slide_count} slides")
        return result

    except Exception as e:
        log.error(f"Ошибка при разборе содержимого презентации: {e}")
        raise RuntimeError(f"Сбой парсинга слайдов: {e}") from e


if __name__ == "__main__":
    import sys
    
    test_path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    
    try:
        test_result = parse_pptx(test_path)
        for s in test_result.slides:
            print(f"Slide {s.slide_index}: {s.shape_count} shapes, {s.image_count} images, texts: {s.texts[:2]}")
    except Exception as err:
        print(f"Test failed: {err}")