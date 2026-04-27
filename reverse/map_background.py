import os
import sys
import json
import logging
import requests
from pathlib import Path
from typing import Optional, Union

import PIL.Image
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

GEO_EXTRACT_PROMPT = """
Посмотри на эту карту и определи её географический центр и масштаб.
Верни СТРОГО JSON без markdown:
{
"center_lat": число (широта центра карты),
"center_lon": число (долгота центра карты),
"zoom": число от 1 до 20 (1=весь мир, 5=страна, 10=город, 15=район, 18=улица),
"region_name": "название региона на карте"
}
"""

class GeoInfo(BaseModel):
    """Географическая информация извлечённая из карты."""
    center_lat: float
    center_lon: float
    zoom: int
    region_name: str

class BackgroundResult(BaseModel):
    """Результат замены подложки."""
    strategy: str
    new_image_path: Optional[str] = None
    original_image_path: str
    geo_info: Optional[GeoInfo] = None
    success: bool = True
    error: Optional[str] = None

def _extract_geo_info(image_path: Union[str, Path]) -> GeoInfo:
    """Использует Gemini Vision чтобы определить координаты и зум карты."""
    load_dotenv()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

    try:
        with PIL.Image.open(image_path) as img:
            response = model.generate_content([GEO_EXTRACT_PROMPT, img])
            text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            return GeoInfo(**data)
    except Exception as e:
        logger.error(f"Ошибка при извлечении геоданных из {image_path}: {e}")
        raise

def _replace_with_mapbox(image_path: Union[str, Path], output_dir: Union[str, Path]) -> BackgroundResult:
    """Заменяет подложку через Mapbox Static API с сохранением пропорций оригинала."""
    try:
        geo = _extract_geo_info(image_path)
        token = os.getenv("MAPBOX_ACCESS_TOKEN")
        if not token:
            return BackgroundResult(strategy="mapbox", original_image_path=str(image_path), success=False, error="MAPBOX_ACCESS_TOKEN не найден")

        with PIL.Image.open(image_path) as img:
            width, height = img.size

        if width > 1280 or height > 1280:
            ratio = min(1280 / width, 1280 / height)
            width = int(width * ratio)
            height = int(height * ratio)
        url = f"https://api.mapbox.com/styles/v1/mapbox/light-v11/static/{geo.center_lon},{geo.center_lat},{geo.zoom},0/{width}x{height}@2x?access_token={token}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return BackgroundResult(strategy="mapbox", original_image_path=str(image_path), success=False, error=f"Mapbox API error: {response.text}")

        output_file = Path(output_dir) / "new_background.jpg"
        with open(output_file, "wb") as f:
            f.write(response.content)

        return BackgroundResult(strategy="mapbox", new_image_path=str(output_file), original_image_path=str(image_path), geo_info=geo)
    except Exception as e:
        logger.error(f"Критическая ошибка Mapbox: {e}")
        return BackgroundResult(strategy="mapbox", original_image_path=str(image_path), success=False, error=str(e))

def replace_background(image_path: Union[str, Path], strategy: str, output_dir: Union[str, Path], accent_color: str = "#0066CC") -> BackgroundResult:
    """Главная функция — выбирает стратегию и выполняет замену."""
    if strategy == "keep":
        return BackgroundResult(strategy="keep", original_image_path=str(image_path))

    strategies = {
        "mapbox": _replace_with_mapbox,
        "nano_banana": lambda ip, od: BackgroundResult(strategy="nano_banana", original_image_path=str(ip), success=False, error="НБ2 ещё не реализован"),
        "svg_world": lambda ip, od: BackgroundResult(strategy="svg_world", original_image_path=str(ip), success=False, error="SVG world ещё не реализован"),
        "svg_country": lambda ip, od: BackgroundResult(strategy="svg_country", original_image_path=str(ip), success=False, error="SVG country ещё не реализован"),
        "programmatic": lambda ip, od: BackgroundResult(strategy="programmatic", original_image_path=str(ip), success=False, error="Programmatic ещё не реализован"),
        "detect_subtype": lambda ip, od: BackgroundResult(strategy="detect_subtype", original_image_path=str(ip), success=False, error="Detect subtype ещё не реализован")
    }

    if strategy in strategies:
        return strategies[strategy](image_path, output_dir)

    return BackgroundResult(strategy=strategy, original_image_path=str(image_path), success=False, error=f"Неизвестная стратегия: {strategy}")

if __name__ == "__main__":
    img_arg = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/layers/background_slide_1.png"
    strat_arg = sys.argv[2] if len(sys.argv) > 2 else "mapbox"
    out_dir = Path("projects/test_map/output")
    out_dir.mkdir(parents=True, exist_ok=True)

    res = replace_background(img_arg, strat_arg, out_dir)
    print(f"Стратегия: {res.strategy}")
    print(f"Успех: {res.success}")
    if res.new_image_path: print(f"Новая подложка: {res.new_image_path}")
    if res.geo_info: print(f"Регион: {res.geo_info.region_name}, координаты: {res.geo_info.center_lat}, {res.geo_info.center_lon}, zoom: {res.geo_info.zoom}")
    if res.error: print(f"Ошибка: {res.error}")