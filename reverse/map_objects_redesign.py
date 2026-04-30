"""Модуль для пересчета координат объектов при замене карты-подложки на слайде."""

import logging
from typing import Optional
from pydantic import BaseModel

from reverse.map_layer_splitter import ShapeInfo
from reverse.map_background import GeoInfo

logger = logging.getLogger(__name__)

TOLERANCE_LOWER = -0.05
TOLERANCE_UPPER = 1.05


class RedesignedObject(BaseModel):
    """Один пересаженный объект с новыми координатами."""
    name: str
    shape_type: str
    rel_x: float
    rel_y: float
    rel_width: float
    rel_height: float
    pixel_x: int
    pixel_y: int
    pixel_width: int
    pixel_height: int
    lat: Optional[float] = None
    lon: Optional[float] = None
    text: Optional[str] = None
    has_fill: bool = False
    out_of_bounds: bool = False


class ObjectsRedesignResult(BaseModel):
    """Результат пересадки всех объектов."""
    total_objects: int
    redesigned: list[RedesignedObject]
    out_of_bounds_count: int
    success: bool = True
    error: Optional[str] = None


def _process_single_object(
    obj: ShapeInfo, bg: ShapeInfo, new_w: int, new_h: int, geo: Optional[GeoInfo]
) -> RedesignedObject:
    """Пересчитывает координаты и параметры для одного объекта."""
    rel_x = (obj.left - bg.left) / bg.width
    rel_y = (obj.top - bg.top) / bg.height
    rel_w = obj.width / bg.width
    rel_h = obj.height / bg.height

    lat, lon = None, None
    if geo:
        cx, cy = rel_x + rel_w / 2, rel_y + rel_h / 2
        lon = geo.west + cx * (geo.east - geo.west)
        lat = geo.north - cy * (geo.north - geo.south)

    oob = (rel_x < TOLERANCE_LOWER or rel_x > TOLERANCE_UPPER or 
           rel_y < TOLERANCE_LOWER or rel_y > TOLERANCE_UPPER)

    return RedesignedObject(
        name=obj.name, shape_type=obj.shape_type, text=obj.text, has_fill=obj.has_fill,
        rel_x=rel_x, rel_y=rel_y, rel_width=rel_w, rel_height=rel_h,
        pixel_x=int(rel_x * new_w), pixel_y=int(rel_y * new_h),
        pixel_width=int(rel_w * new_w), pixel_height=int(rel_h * new_h),
        lat=lat, lon=lon, out_of_bounds=oob
    )


def redesign_objects(
    objects: list[ShapeInfo],
    background: ShapeInfo,
    new_bg_width: int,
    new_bg_height: int,
    geo_info: Optional[GeoInfo] = None,
) -> ObjectsRedesignResult:
    """Главная функция для пересадки списка объектов на новую подложку."""
    logger.info(f"Начало пересадки объектов. Всего объектов: {len(objects)}")
    try:
        redesigned_list = []
        out_of_bounds_count = 0

        for obj in objects:
            logger.info(f"Обработка объекта: {obj.name}")
            new_obj = _process_single_object(obj, background, new_bg_width, new_bg_height, geo_info)
            redesigned_list.append(new_obj)
            if new_obj.out_of_bounds:
                out_of_bounds_count += 1

        logger.info("Пересадка объектов успешно завершена.")
        return ObjectsRedesignResult(
            total_objects=len(objects),
            redesigned=redesigned_list,
            out_of_bounds_count=out_of_bounds_count
        )

    except Exception as e:
        logger.error(f"Критическая ошибка при пересадке объектов: {e}")
        return ObjectsRedesignResult(
            total_objects=len(objects),
            redesigned=[],
            out_of_bounds_count=0,
            success=False,
            error=str(e)
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Для теста предполагается, что импортированные модели поддерживают такую инициализацию
    mock_bg = ShapeInfo(
        name="Map Background", shape_type="picture", 
        left=1.0, top=1.0, width=8.0, height=6.0, area=48.0
    )
    
    mock_objects = [
        ShapeInfo(
            name="Point A", shape_type="auto_shape", left=5.0, top=4.0, 
            width=0.5, height=0.5, area=0.25, has_fill=True
        ),
        ShapeInfo(
            name="Out of bounds Point", shape_type="auto_shape", left=-1.0, top=1.0, 
            width=0.5, height=0.5, area=0.25
        )
    ]
    
    mock_geo = GeoInfo(
        center_lat=51.1694, center_lon=71.4491, region_name="Astana",
        south=51.0, north=51.3, west=71.2, east=71.7
    )
    
    result = redesign_objects(
        objects=mock_objects, background=mock_bg, 
        new_bg_width=1920, new_bg_height=1080, geo_info=mock_geo
    )
    
    logger.info(f"Результат: {result.model_dump_json(indent=2)}")