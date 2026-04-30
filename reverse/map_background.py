"""
map_background.py — Замена подложки карты.
Подход: Gemini OCR → Nominatim → bbox → большая карта → Edge Matching → точный bbox → финальная карта.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np
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

# === Провайдер карт ===
# Единственное место для смены провайдера (Mapbox → MapTiler и т.д.)
TILE_STYLES = {
    "streets": (
        "https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/"
        "[{west},{south},{east},{north}]/{w}x{h}"
        "?access_token={token}&attribution=false&logo=false"
    ),
    "light": (
        "https://api.mapbox.com/styles/v1/mapbox/light-v11/static/"
        "[{west},{south},{east},{north}]/{w}x{h}@2x"
        "?access_token={token}&attribution=false&logo=false"
    ),
}


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


# =====================================================
# Gemini OCR + Nominatim (без изменений)
# =====================================================

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
    """Nominatim геокодирование. Два прохода: строгий + мягкий для ненайденных."""
    headers = {"User-Agent": "PPTX-AI/1.0 (pptx-ai@project.com)"}
    
    # --- Проход 1: строгий viewbox ---
    viewbox = f"{center_lon - radius},{center_lat + radius},{center_lon + radius},{center_lat - radius}"
    found = []
    not_found = []

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
                found.append({"name": place, "lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])})
                logger.info(f"  {place}: {data[0]['lat']}, {data[0]['lon']}")
            else:
                not_found.append(place)
                logger.warning(f"  {place}: НЕ НАЙДЕН (проход 1)")
        except Exception as e:
            not_found.append(place)
            logger.warning(f"  {place}: ошибка — {e}")
        time.sleep(1.1)

    # --- Проход 2: мягкий viewbox для ненайденных ---
    if not_found and found:
        logger.info(f"Проход 2: ищем {len(not_found)} ненайденных с расширенным viewbox...")
        # Строим viewbox из уже найденных точек
        lats = [p["lat"] for p in found]
        lons = [p["lon"] for p in found]
        vb_center_lat = (min(lats) + max(lats)) / 2
        vb_center_lon = (min(lons) + max(lons)) / 2
        # Радиус = максимальное расстояние от центра * 3
        vb_radius = max(
            max(lats) - min(lats),
            max(lons) - min(lons),
        ) * 1.5 + 0.5  # запас
        wide_viewbox = (
            f"{vb_center_lon - vb_radius},{vb_center_lat + vb_radius},"
            f"{vb_center_lon + vb_radius},{vb_center_lat - vb_radius}"
        )

        for place in not_found:
            try:
                resp = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": place, "format": "json", "limit": 1, "viewbox": wide_viewbox, "bounded": 0},
                    headers=headers,
                    timeout=10,
                )
                data = resp.json()
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    # Фильтр: не дальше 500 км (~4.5 градусов) от центра найденных
                    if abs(lat - vb_center_lat) < 4.5 and abs(lon - vb_center_lon) < 4.5:
                        found.append({"name": place, "lat": lat, "lon": lon})
                        logger.info(f"  {place}: {lat}, {lon} (проход 2)")
                    else:
                        logger.warning(f"  {place}: слишком далеко ({lat}, {lon}), отброшен")
                else:
                    logger.warning(f"  {place}: НЕ НАЙДЕН (проход 2)")
            except Exception as e:
                logger.warning(f"  {place}: ошибка — {e}")
            time.sleep(1.1)

    return found


def _calc_bbox(points: list[dict], padding_pct: float = 0.05) -> dict:
    """Вычисляет bounding box из точек + padding."""
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]

    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)

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


# =====================================================
# Провайдер карт
# =====================================================

def _download_map_tile(
    bbox: dict, width: int, height: int, style: str, token: str, output_path: Path
) -> str:
    """Скачивает карту от провайдера. Менять здесь при смене на MapTiler."""
    width = min(1280, width)
    height = min(1280, height)

    if style not in TILE_STYLES:
        raise ValueError(f"Неизвестный стиль: {style}. Доступные: {list(TILE_STYLES.keys())}")

    url = TILE_STYLES[style].format(
        west=bbox["west"], south=bbox["south"],
        east=bbox["east"], north=bbox["north"],
        w=width, h=height, token=token,
    )

    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        raise Exception(f"Провайдер карт ошибка {resp.status_code}: {resp.text[:200]}")

    with open(output_path, "wb") as f:
        f.write(resp.content)

    return str(output_path)


# =====================================================
# Edge Matching
# =====================================================

def _edge_match(original_image_path: Union[str, Path], big_map_path: Union[str, Path], expand_ratio: float) -> dict:
    """Edge matching: находит точную позицию оригинала на большой карте."""
    orig = cv2.imread(str(original_image_path))
    big = cv2.imread(str(big_map_path))

    if orig is None:
        raise Exception(f"Не удалось прочитать: {original_image_path}")
    if big is None:
        raise Exception(f"Не удалось прочитать: {big_map_path}")

    h_orig, w_orig = orig.shape[:2]
    h_big, w_big = big.shape[:2]

    # Edge маски
    orig_edges = cv2.Canny(
        cv2.GaussianBlur(cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY), (5, 5), 0), 30, 100
    )
    big_edges = cv2.Canny(
        cv2.GaussianBlur(cv2.cvtColor(big, cv2.COLOR_BGR2GRAY), (5, 5), 0), 30, 100
    )

    kernel = np.ones((3, 3), np.uint8)
    orig_edges = cv2.dilate(orig_edges, kernel, iterations=2)
    big_edges = cv2.dilate(big_edges, kernel, iterations=2)

    # Ожидаемый масштаб
    target_ratio = 1.0 / (1.0 + 2.0 * expand_ratio)
    expected_scale = (
        (w_big * target_ratio) / w_orig + (h_big * target_ratio) / h_orig
    ) / 2

    low = max(0.2, expected_scale * 0.5)
    high = min(4.0, expected_scale * 1.5)
    scales = np.arange(low, high, 0.02)

    best_val = -1
    best_loc = None
    best_scale = None

    for scale in scales:
        new_w = int(w_orig * scale)
        new_h = int(h_orig * scale)
        if new_w >= w_big or new_h >= h_big or new_w < 50 or new_h < 50:
            continue
        resized = cv2.resize(orig_edges, (new_w, new_h), interpolation=cv2.INTER_AREA)
        result = cv2.matchTemplate(big_edges, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_val:
            best_val = max_val
            best_loc = max_loc
            best_scale = scale

    tw = int(w_orig * best_scale)
    th = int(h_orig * best_scale)

    return {
        "confidence": best_val,
        "position": best_loc,
        "scale": best_scale,
        "template_size": (tw, th),
    }


def _calc_precise_bbox(match_result: dict, big_bbox: dict, big_image_size: tuple) -> dict:
    """Пересчитывает пиксельную позицию в точный GPS bbox."""
    x, y = match_result["position"]
    tw, th = match_result["template_size"]
    w_big, h_big = big_image_size

    lon_per_pixel = (big_bbox["east"] - big_bbox["west"]) / w_big
    lat_per_pixel = (big_bbox["north"] - big_bbox["south"]) / h_big

    return {
        "south": big_bbox["north"] - (y + th) * lat_per_pixel,
        "north": big_bbox["north"] - y * lat_per_pixel,
        "west": big_bbox["west"] + x * lon_per_pixel,
        "east": big_bbox["west"] + (x + tw) * lon_per_pixel,
    }


# =====================================================
# Главная стратегия: mapbox
# =====================================================

def _replace_with_mapbox(image_path: Union[str, Path], output_dir: Union[str, Path]) -> BackgroundResult:
    """Полный пайплайн: OCR → bbox → Edge Matching → точный bbox → финальная карта."""
    str_path = str(image_path)
    output_dir = Path(output_dir)
    import hashlib
    img_hash = hashlib.md5(Path(image_path).read_bytes()).hexdigest()[:8]
    cache_path = Path(output_dir) / f"geo_cache_{img_hash}.json"

    # --- Проверка кэша ---
    cache_data = None
    if cache_path.exists():
        logger.info("Используем кэш geo_cache.json")
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            center_lat = cache_data["center_lat"]
            center_lon = cache_data["center_lon"]
            region_name = cache_data["region_name"]
            place_names = cache_data["place_names"]
            bbox = cache_data["bbox"]
            geocoded = cache_data.get("geocoded", [])
        except Exception as e:
            logger.warning(f"Ошибка чтения кэша: {e}. Данные будут пересобраны.")
            cache_data = None

    if not cache_data:
        logger.info("Кэш не найден, запускаем Gemini OCR")
        # --- Шаг 1: Gemini OCR ---
        try:
            logger.info("Шаг 1: Gemini OCR — извлекаем названия мест...")
            extracted = _extract_places_and_center(image_path)
            center_lat = extracted["center_lat"]
            center_lon = extracted["center_lon"]
            region_name = extracted.get("region_name", "Unknown")
            place_names = extracted.get("place_names", [])
            logger.info(f"  Центр: {center_lat}, {center_lon} | Мест: {len(place_names)}")
        except Exception as e:
            return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Gemini OCR: {e}")

        if len(place_names) < 2:
            return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error="Менее 2 мест найдено")

        # --- Шаг 2: Nominatim ---
        logger.info("Шаг 2: Nominatim геокодирование...")
        geocoded = _geocode_with_viewbox(place_names, center_lat, center_lon)
        if len(geocoded) < 2:
            return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Геокодировано {len(geocoded)}, мало для bbox")
        logger.info(f"  Геокодировано: {len(geocoded)} из {len(place_names)}")

        # --- Шаг 3: BBox из точек ---
        bbox = _calc_bbox(geocoded, padding_pct=0.05)
        logger.info(f"Шаг 3: BBox точек: S={bbox['south']:.4f} N={bbox['north']:.4f} W={bbox['west']:.4f} E={bbox['east']:.4f}")

        # --- Сохранение кэша ---
        try:
            cache_content = {
                "center_lat": center_lat,
                "center_lon": center_lon,
                "region_name": region_name,
                "place_names": place_names,
                "bbox": bbox,
                "geocoded": geocoded
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_content, f, ensure_ascii=False, indent=4)
            logger.info("Кэш сохранен в geo_cache.json")
        except Exception as e:
            logger.warning(f"Не удалось сохранить кэш: {e}")

    # --- Шаг 4: Расширяем bbox ---
    expand = 0.5
    lat_range = bbox["north"] - bbox["south"]
    lon_range = bbox["east"] - bbox["west"]
    big_bbox = {
        "south": bbox["south"] - lat_range * expand,
        "north": bbox["north"] + lat_range * expand,
        "west": bbox["west"] - lon_range * expand,
        "east": bbox["east"] + lon_range * expand,
    }
    logger.info(f"Шаг 4: Расширенный bbox (+{int(expand*100)}%)")

    # --- Шаг 5: Большая карта для matching ---
    token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not token:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error="MAPBOX_ACCESS_TOKEN не найден")

    with PIL.Image.open(image_path) as img:
        orig_w, orig_h = img.size

    big_w = min(1280, orig_w * 2)
    big_h = min(1280, orig_h * 2)
    match_ref_path = output_dir / "match_reference.png"

    try:
        logger.info(f"Шаг 5: Скачиваем streets для matching ({big_w}x{big_h})...")
        _download_map_tile(big_bbox, big_w, big_h, "streets", token, match_ref_path)
    except Exception as e:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Скачивание streets: {e}")

    # Реальный размер скачанной карты
    big_img = cv2.imread(str(match_ref_path))
    h_big_actual, w_big_actual = big_img.shape[:2]

    # --- Шаг 6: Edge Matching ---
    try:
        logger.info("Шаг 6: Edge Matching...")
        match_result = _edge_match(image_path, match_ref_path, expand)
        logger.info(f"  Confidence: {match_result['confidence']:.4f}, Scale: {match_result['scale']:.2f}")
    except Exception as e:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Edge matching: {e}")

    # --- Шаг 7: Точный bbox ---
    if match_result["confidence"] >= 0.05:
        precise_bbox = _calc_precise_bbox(match_result, big_bbox, (w_big_actual, h_big_actual))
        logger.info(f"Шаг 7: Точный bbox: S={precise_bbox['south']:.4f} N={precise_bbox['north']:.4f} W={precise_bbox['west']:.4f} E={precise_bbox['east']:.4f}")
    else:
        logger.warning(f"Шаг 7: Matching слабый ({match_result['confidence']:.4f}), используем исходный bbox")
        precise_bbox = bbox

    # --- Шаг 8: Финальная карта ---
    final_w = min(1280, orig_w)
    final_h = min(1280, orig_h)
    final_path = output_dir / "new_background.png"
    final_style = "light"

    try:
        logger.info(f"Шаг 8: Финальная карта {final_style} ({final_w}x{final_h}@2x)...")
        _download_map_tile(precise_bbox, final_w, final_h, final_style, token, final_path)
    except Exception as e:
        return BackgroundResult(strategy="mapbox", original_image_path=str_path, success=False, error=f"Финальная карта: {e}")

    # Удаляем временную карту
    try:
        match_ref_path.unlink()
    except Exception:
        pass

    # --- Шаг 9: Результат ---
    geo_info = GeoInfo(
        center_lat=center_lat,
        center_lon=center_lon,
        region_name=region_name,
        place_names=place_names,
        south=precise_bbox["south"],
        north=precise_bbox["north"],
        west=precise_bbox["west"],
        east=precise_bbox["east"],
    )

    logger.info(f"Готово! Сохранено: {final_path}")
    return BackgroundResult(strategy="mapbox", new_image_path=str(final_path), original_image_path=str_path, geo_info=geo_info)


# =====================================================
# Точка входа
# =====================================================

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
        print(f"BBox: S={res.geo_info.south:.4f} N={res.geo_info.north:.4f} W={res.geo_info.west:.4f} E={res.geo_info.east:.4f}")
    if res.error:
        print(f"Ошибка: {res.error}")