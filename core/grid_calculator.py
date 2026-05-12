"""Модуль для расчета геометрии 12-колоночной сетки слайда."""

import logging
from typing import Any

from models.contracts import LayoutPlan, RowInstruction, ColumnInstruction, FooterInstruction

logger = logging.getLogger(__name__)

SLIDE_W = 1280
SLIDE_H = 720
MARGIN_H = 43
MARGIN_V = 20
COL_W = 76
GAP = 26
WORK_W = 1194  
WORK_H = 680   

SPAN_TO_WIDTH = {
    3: 280,
    4: 382,
    5: 480,
    6: 582,
    7: 688,
    8: 790,
    12: 1194
}


def calc_row_geometry(row: RowInstruction, y_offset: int) -> list[dict[str, Any]]:
    """Вычисляет координаты x, y и ширину w для каждой колонки в ряду."""
    try:
        logger.info(f"Расчет геометрии ряда с y_offset={y_offset}")
        result = []
        current_x = MARGIN_H

        for col in row.columns:
            width = SPAN_TO_WIDTH.get(col.grid_span, 100)
            
            col_data = {
                "col_id": col.col_id,
                "object_type": col.object_type,
                "x": current_x,
                "y": y_offset,
                "w": width,
                "content": col.content,
                "render": col.render,
                "visual_subtype": col.visual_subtype
            }
            result.append(col_data)
            current_x += width + GAP

        return result
    except Exception as e:
        logger.error(f"Ошибка при расчете геометрии ряда: {e}")
        raise


def calc_layout_geometry(plan: LayoutPlan) -> dict[str, Any]:
    """Преобразует абстрактный план в финальные координаты элементов на сетке."""
    try:
        logger.info(f"Начало расчета геометрии LayoutPlan, индекс: {plan.slide_index}")
        
        if plan.header_type == "A":
            y_start = 20 + 80 + GAP 
        else:
            y_start = MARGIN_V 

        heading_rows = [r for r in plan.rows if any(c.object_type == "heading" for c in r.columns)]
        other_rows = [r for r in plan.rows if not any(c.object_type == "heading" for c in r.columns)]
        
        num_others = len(other_rows) if other_rows else 1
        
        bottom_limit = SLIDE_H - MARGIN_V
        if plan.needs_footer:
            bottom_limit -= (20 + GAP)
            
        used_by_headings = len(heading_rows) * (70 + GAP)
        available_h = bottom_limit - y_start - used_by_headings
        row_height = (available_h / num_others) - GAP if num_others > 0 else 100

        calculated_rows = []
        current_y = y_start
        
        for row in plan.rows:
            is_heading = any(c.object_type == "heading" for c in row.columns)
            h = 70 if is_heading else row_height
            
            row_geom = calc_row_geometry(row, int(current_y))
            for obj in row_geom:
                obj["h"] = int(h)
                obj["row_id"] = row.row_id
                
            calculated_rows.append(row_geom)
            current_y += h + GAP

        footer_data = None
        if plan.needs_footer:
            footer_y = SLIDE_H - MARGIN_V - 20
            footer_data = {
                "y": footer_y,
                "left": plan.footer.left if plan.footer else "",
                "right": plan.footer.right if plan.footer else ""
            }

        return {
            "rows": calculated_rows,
            "footer": footer_data,
            "header_type": plan.header_type,
            "style_mode": plan.style_mode,
            "slide_index": plan.slide_index
        }

    except Exception as e:
        logger.error(f"Ошибка при расчете геометрии макета: {e}")
        raise


if __name__ == "__main__":
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    test_rows = [
        RowInstruction(
            row_id="r0",
            columns=[
                ColumnInstruction(
                    col_id="c0", grid_span=12, object_type="heading", 
                    content={"title": "ТЕСТ"}, render="ai"
                )
            ]
        ),
        RowInstruction(
            row_id="r1",
            columns=[
                ColumnInstruction(
                    col_id="c1", grid_span=7, object_type="table", 
                    content={"headers": ["A", "B"]}, render="ai"
                ),
                ColumnInstruction(
                    col_id="c2", grid_span=5, object_type="chart", 
                    visual_subtype="bar", content={"chart_type": "bar"}, render="external"
                )
            ]
        )
    ]
    
    test_plan = LayoutPlan(
        slide_index=0,
        header_type="B",
        composition_schema="A",
        rows=test_rows,
        style_mode="soft",
        needs_footer=False
    )
    
    try:
        geometry = calc_layout_geometry(test_plan)
        print(json.dumps(geometry, indent=2, ensure_ascii=False))
    except Exception as err:
        logger.error(f"Тест провален: {err}")