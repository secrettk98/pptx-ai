import json
import logging
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR_TYPE

logger = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> RGBColor:
    """
    Преобразует строку hex (например "#F5A623") в объект RGBColor.

    :param hex_color: Цвет в формате hex.
    :return: Объект RGBColor.
    """
    hex_color = hex_color.lstrip("#")
    return RGBColor(
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16)
    )


def set_slide_dimensions(prs: Presentation, slide_data: dict) -> None:
    """
    Устанавливает размеры презентации на основе данных из JSON.

    :param prs: Объект презентации.
    :param slide_data: Словарь с данными слайда.
    """
    prs.slide_width = Inches(slide_data["width_inches"])
    prs.slide_height = Inches(slide_data["height_inches"])


def set_slide_background(slide, bg_color: str) -> None:
    """
    Устанавливает цвет фона слайда.

    :param slide: Объект слайда.
    :param bg_color: Цвет фона в формате hex.
    """
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = hex_to_rgb(bg_color)


def add_shape_element(slide, element: dict) -> None:
    """
    Добавляет фигуру на слайд.

    :param slide: Объект слайда.
    :param element: Данные элемента фигуры.
    """
    shape_type_map = {
        "rounded_rectangle": MSO_SHAPE.ROUNDED_RECTANGLE,
        "diamond": MSO_SHAPE.DIAMOND
    }
    shape_type = shape_type_map.get(element["shape_type"])

    if not shape_type:
        logger.warning(f"Unknown shape type: {element['shape_type']}")
        return

    shape = slide.shapes.add_shape(
        shape_type,
        Inches(element["left_inches"]),
        Inches(element["top_inches"]),
        Inches(element["width_inches"]),
        Inches(element["height_inches"])
    )

    if "fill_color" in element and element["fill_color"]:
        shape.fill.solid()
        shape.fill.fore_color.rgb = hex_to_rgb(element["fill_color"])

    if element.get("border") == "none":
        shape.line.fill.background()

    if "corner_radius_inches" in element:
        min_side = min(element["width_inches"], element["height_inches"])
        adjustment_value = element["corner_radius_inches"] / min_side
        if adjustment_value > 0.5:
            adjustment_value = 0.5
        shape.adjustments[0] = adjustment_value

    logger.debug(f"Added shape: {element['id']}")


def add_line_element(slide, element: dict) -> None:
    """
    Добавляет линию (коннектор) на слайд.

    :param slide: Объект слайда.
    :param element: Данные элемента линии.
    """
    start_left = Inches(element["start_left_inches"])
    start_top = Inches(element["start_top_inches"])
    end_left = Inches(element["end_left_inches"])
    end_top = Inches(element["end_top_inches"])

    connector = slide.shapes.add_connector(
        MSO_CONNECTOR_TYPE.STRAIGHT,
        start_left, start_top, end_left, end_top
    )

    connector.line.color.rgb = hex_to_rgb(element["line_color"])
    connector.line.width = Pt(element["line_width_pt"])

    logger.debug(f"Added line: {element['id']}")


def add_text_box_element(slide, element: dict) -> None:
    """
    Добавляет текстовый бокс на слайд с поддержкой форматирования и выравнивания.

    :param slide: Объект слайда.
    :param element: Данные элемента текстового бокса.
    """
    txBox = slide.shapes.add_textbox(
        Inches(element["left_inches"]),
        Inches(element["top_inches"]),
        Inches(element["width_inches"]),
        Inches(element["height_inches"])
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE

    if "vertical_alignment" in element:
        anchor_map = {"middle": "ctr", "top": "t", "bottom": "b"}
        bodyPr = tf._txBody.bodyPr
        bodyPr.set("anchor", anchor_map[element["vertical_alignment"]])

    alignment_map = {
        "center": PP_ALIGN.CENTER,
        "left": PP_ALIGN.LEFT,
        "right": PP_ALIGN.RIGHT
    }
    alignment = alignment_map.get(element.get("alignment"))

    text_runs = element.get("text_runs", [])
    if not text_runs:
        return

    p = tf.paragraphs[0]
    if alignment:
        p.alignment = alignment

    for i, run_data in enumerate(text_runs):
        if i > 0:
            prev_run = text_runs[i-1]
            if prev_run["text"].endswith("\n"):
                p = tf.add_paragraph()
                if alignment:
                    p.alignment = alignment

        run = p.add_run()
        run.text = run_data["text"].rstrip("\n")
        run.font.name = run_data["font_name"]
        run.font.size = Pt(run_data["font_size_pt"])
        run.font.bold = run_data["bold"]
        run.font.color.rgb = hex_to_rgb(run_data["color"])

    logger.debug(f"Added text_box: {element['id']}")


def build_slide_from_json(json_path: Path, output_path: Path) -> None:
    """
    Основная функция для сборки слайда из JSON файла.

    :param json_path: Путь к JSON файлу с данными.
    :param output_path: Путь для сохранения результирующей презентации.
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    prs = Presentation()

    set_slide_dimensions(prs, data["slide"])

    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    set_slide_background(slide, data["slide"]["background_color"])

    for element in data["elements"]:
        etype = element["type"]
        if etype == "shape":
            add_shape_element(slide, element)
        elif etype == "line":
            add_line_element(slide, element)
        elif etype == "text_box":
            add_text_box_element(slide, element)
        else:
            logger.warning(f"Unknown element type: {etype}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    logger.info(f"Slide built and saved to {output_path}")
