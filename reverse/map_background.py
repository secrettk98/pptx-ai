"""
map_background.py — Замена подложки карты.
Рабочий подход: Gemini OCR → названия мест → Gemini центр → Nominatim + viewbox → bbox + 5% padding → Mapbox.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional, Union

import requests
import PIL.Image
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.1-flash-lite-preview"

PLACES_PROMPT = """Посмотри на эту карту. Найди все названия мест (города, районы, улицы, объекты).
Также определи примерный географический центр карты.
Верни СТРОГО JSON без markdown:
{
    "center_lat": число (широта центра),
    "center_lon": число (долгота центра),
    "region_name": "название региона",
    "place_names": ["список всех названий мест которые ты видишь на карте"]
}"""


class GeoInfo(BaseModel):
    """Географическая информация."""
    center_lat: float
    center_lon: float
    region_name: str
    place_names: list[str] = []
    south: float = 0.0
    north: float = 0.0
    west: float = 0.0
    east: float = 0.0


class BackgroundResult(BaseModel):
    """Результат замены подложки."""
    strategy: str
    new_image_path: Optional[str] = None
    original_image_path: str
    geo_info: Optional[GeoInfo] = None
    success: bool = True
    error: Optional[str] = None


def _extract_places_and_center(image_path: Union[str, Path]) -> dict:
    """Gemini OCR: читает названия мест + определяет грубый центр."""
    load_dotenv()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(GEMINI_MODEL)

    with PIL.Image.open(image_path) as img:
        response = model.generate_content([PLACES_PROMPT, img])

    text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _geocode_with_viewbox(
    place_names: list[str], center_lat: float, center_lon: float, radius: float = 0.2
) -> list[dict]:
    """Nominatim геокодирование с viewbox привязкой к центру."""
    viewbox = f"{center_lon - radius},{center_lat + radius},{center_lon + radius},{center_lat - radius}"
    headers = {"User-Agent": "PPTX-AI/1.0 (pptx-ai@project.com)"}
    results = []

    for place in place_names:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": place, "format": "json", "limit": 1, "viewbox": viewbox, "bounded": 1},
                headers=headers,
                timeout=10,
            )
            data = resp.json()
            if data:
                results.append({
                    "name": place,
                    "lat": float(data[0]["lat"]),
                    "lon": float(data[0]["lon"]),
                })
                logger.info(f"  {place}: {data[0]['lat']}, {data[0]['lon']}")
            else:
                logger.warning(f"  {place}: НЕ НАЙДЕН")
        except Exception as e:
            logger.warning(f"  {place}: ошибка — {e}")
        time.sleep(1.1)

    return results


def _calc_bbox(points: list[dict], padding_pct: float = 0.05) -> dict:
    """Вычисляет bounding box из точек + padding."""
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]

    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)

    # Минимальный диапазон чтобы не было точки
    if lat_range < 0.01:
        lat_range = 0.05
    if lon_range < 0.01:
        lon_range = 0.05

    padding_lat = lat_range * padding_pct
    padding_lon = lon_range * padding_pct

    return {
        "south": min(lats) - padding_lat,
        "north": max(lats) + padding_lat,
        "west": min(lons) - padding_lon,
        "east": max(lons) + padding_lon,
    }


def _replace_with_mapbox(image_path: Union[str, Path], output_dir: Union[str, Path]) -> BackgroundResult:
    """Заменяет подложку: Gemini OCR → Nominatim bbox → Mapbox."""
    str_path = str(image_path)

    # 1. Gemini OCR → названия мест + грубый центр
    try:
        logger.info("Шаг 1: Gemini OCR — извлекаем названия мест...")
        extracted = _extract_places_and_center(image_path)
        center_lat = extracted["center_lat"]
        center_lon = extracted["center_lon"]
        region_name = extracted.get("region_name", "Unknown")
        place_names = extracted.get("place_names", [])
        logger.info(f"  Центр: {center_lat}, {center_lon} | Мест найдено: {len(place_names)}")
    except Exception as e:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Gemini OCR ошибка: {e}")

    if len(place_names) < 2:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error="Gemini нашёл менее 2 мест, невозможно построить bbox")

    # 2. Nominatim + viewbox → точные GPS
    logger.info("Шаг 2: Nominatim геокодирование с viewbox...")
    geocoded = _geocode_with_viewbox(place_names, center_lat, center_lon)

    if len(geocoded) < 2:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Геокодировано {len(geocoded)} из {len(place_names)}, мало для bbox")

    logger.info(f"  Геокодировано: {len(geocoded)} из {len(place_names)}")

    # 3. BBox + 5% padding
    bbox = _calc_bbox(geocoded, padding_pct=0.05)
    logger.info(f"  BBox: S={bbox['south']:.4f} N={bbox['north']:.4f} W={bbox['west']:.4f} E={bbox['east']:.4f}")

    # 4. Размер из оригинала
    with PIL.Image.open(image_path) as img:
        width, height = img.size
    if width > 1280 or height > 1280:
        ratio = min(1280 / width, 1280 / height)
        width = int(width * ratio)
        height = int(height * ratio)

    # 5. Mapbox Static API с bbox
    token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not token:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error="MAPBOX_ACCESS_TOKEN не найден")

    url = (
        f"https://api.mapbox.com/styles/v1/mapbox/light-v11/static/"
        f"[{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}]"
        f"/{width}x{height}@2x?access_token={token}"
    )

    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Mapbox {response.status_code}: {response.text[:200]}")

        output_file = Path(output_dir) / "new_background.jpg"
        with open(output_file, "wb") as f:
            f.write(response.content)

        geo_info = GeoInfo(
            center_lat=center_lat,
            center_lon=center_lon,
            region_name=region_name,
            place_names=place_names,
            south=bbox["south"],
            north=bbox["north"],
            west=bbox["west"],
            east=bbox["east"],
        )

        logger.info(f"  Сохранено: {output_file}")
        return BackgroundResult(strategy="mapbox", new_image_path=str(output_file), original_image_path=str_path, geo_info=geo_info)

    except Exception as e:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Mapbox запрос: {e}")


def replace_background(
    image_path: Union[str, Path], strategy: str, output_dir: Union[str, Path], accent_color: str = "#0066CC"
) -> BackgroundResult:
    """Главная функция — выбирает стратегию и выполняет замену."""
    str_path = str(image_path)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if strategy == "keep":
        return BackgroundResult(strategy="keep", original_image_path=str_path)

    if strategy == "mapbox":
        return _replace_with_mapbox(image_path, output_dir)

    stubs = ["nano_banana", "svg_world", "svg_country", "programmatic", "detect_subtype"]
    if strategy in stubs:
        return BackgroundResult(strategy=strategy, original_image_path=str_path, success=False, error=f"{strategy} ещё не реализован")

    return BackgroundResult(strategy=strategy, original_image_path=str_path, success=False, error=f"Неизвестная стратегия: {strategy}")


if __name__ == "__main__":
    img_arg = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/layers/background_slide_1.png"
    strat_arg = sys.argv[2] if len(sys.argv) > 2 else "mapbox"
    out_dir = Path("projects/test_map/output")
    out_dir.mkdir(parents=True, exist_ok=True)

    res = replace_background(img_arg, strat_arg, out_dir)
    print(f"\nСтратегия: {res.strategy}")
    print(f"Успех: {res.success}")
    if res.new_image_path:
        print(f"Новая подложка: {res.new_image_path}")
    if res.geo_info:
        print(f"Регион: {res.geo_info.region_name}")
        print(f"Центр: {res.geo_info.center_lat}, {res.geo_info.center_lon}")
        print(f"BBox: S={res.geo_info.south:.4f} N={res.geo_info.north:.4f} W={res.geo_info.west:.4f} E={res.geo_info.east:.4f}")
        print(f"Мест найдено: {len(res.geo_info.place_names)}")
    if res.error:
        print(f"Ошибка: {res.error}")