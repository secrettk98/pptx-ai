import base64
import os
import time
from typing import Literal

import google.generativeai as genai
import polyline
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()


# ─── Промпт для Gemini ───────────────────────────────────────────────
MAP_ANALYSIS_PROMPT = """
You are analyzing a map image from a business presentation.
Extract ALL information and return strict JSON:

{
  "map_type": "route" | "locations" | "coverage_zones" | "political",
  "region_description": "human readable, e.g. Kazakhstan, Europe, Moscow region",
  "bounds": {
    "north": float,
    "south": float,
    "east": float,
    "west": float
  },
  "points": [
    {
      "name": "city or location name in original language",
      "name_en": "English name for geocoding",
      "role": "origin" | "destination" | "waypoint" | "office" | "warehouse" | "generic",
      "label": "any text label near this point on the map"
    }
  ],
  "routes": [
    {
      "from_point": "name matching points[].name",
      "to_point": "name matching points[].name",
      "color_hex": "#FF0000",
      "style": "solid" | "dashed",
      "label": "any label on this route"
    }
  ],
  "zones": [
    {
      "description": "e.g. Western region coverage",
      "color_hex": "#00FF00",
      "opacity": 0.3
    }
  ],
  "legend_items": [
    {
      "color_hex": "#FF0000",
      "label": "text from legend"
    }
  ],
  "title": "map title if visible, else null"
}

Rules:
- bounds: estimate geographic bounding box of the visible map area
- points: list ALL marked cities/locations you can see
- name_en: always provide English transliteration for geocoding
- routes: describe connections between points if lines exist
- zones: describe colored/shaded areas if they exist
- If something is not present, use empty array []
- color_hex: your best guess of the color used
- Return ONLY valid JSON, no markdown
"""


# ─── Pydantic модели ─────────────────────────────────────────────────
class MapPoint(BaseModel):
    name: str
    name_en: str
    role: Literal["origin", "destination", "waypoint", "office", "warehouse", "generic"]
    label: str | None = None


class MapRoute(BaseModel):
    from_point: str
    to_point: str
    color_hex: str = "#0066CC"
    style: Literal["solid", "dashed"] = "solid"
    label: str | None = None


class MapZone(BaseModel):
    description: str
    color_hex: str
    opacity: float = 0.3


class MapLegendItem(BaseModel):
    color_hex: str
    label: str


class MapBounds(BaseModel):
    north: float
    south: float
    east: float
    west: float


class MapAnalysis(BaseModel):
    map_type: Literal["route", "locations", "coverage_zones", "political"]
    region_description: str
    bounds: MapBounds | None = None
    points: list[MapPoint] = []
    routes: list[MapRoute] = []
    zones: list[MapZone] = []
    legend_items: list[MapLegendItem] = []
    title: str | None = None


class GeocodedPoint(BaseModel):
    name: str
    name_en: str
    lat: float
    lon: float
    role: str
    label: str | None = None


# ─── Настройка Gemini ─────────────────────────────────────────────────
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))


# ─── Шаг 1: Vision-анализ карты ──────────────────────────────────────
def analyze_map_image(image_path: str) -> MapAnalysis | None:
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        with open(image_path, "rb") as f:
            image_data = f.read()
        encoded_image = base64.b64encode(image_data).decode("utf-8")

        image_part = {
            "mime_type": "image/jpeg",
            "data": encoded_image,
        }

        response = model.generate_content(
            [MAP_ANALYSIS_PROMPT, image_part],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            ),
        )

        analysis = MapAnalysis.model_validate_json(response.text)
        return analysis

    except FileNotFoundError:
        print(f"Ошибка: Файл не найден: {image_path}")
        return None
    except ValidationError as e:
        print(f"Ошибка валидации JSON от Gemini: {e}")
        return None
    except Exception as e:
        print(f"Ошибка при анализе карты: {e}")
        return None


# ─── Шаг 2: Геокодирование ───────────────────────────────────────────
def geocode_points(points: list[MapPoint]) -> list[GeocodedPoint]:
    geocoded_results = []
    nominatim_url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "PPTX-AI/1.0 (contact@example.com)"}

    for point in points:
        params = {"q": point.name_en, "format": "json", "limit": 1}
        try:
            response = requests.get(nominatim_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data:
                geocoded_results.append(
                    GeocodedPoint(
                        name=point.name,
                        name_en=point.name_en,
                        lat=float(data[0]["lat"]),
                        lon=float(data[0]["lon"]),
                        role=point.role,
                        label=point.label,
                    )
                )
            else:
                print(f"Не найдено: '{point.name_en}'")

        except requests.exceptions.RequestException as e:
            print(f"Ошибка Nominatim для '{point.name_en}': {e}")
        except Exception as e:
            print(f"Ошибка геокодирования '{point.name_en}': {e}")

        time.sleep(1.1)

    return geocoded_results


# ─── Шаг 3: Сборка карты через Mapbox ────────────────────────────────
def generate_map_image(
    geocoded_points: list[GeocodedPoint],
    map_routes: list[MapRoute],
    accent_color: str,
    output_path: str,
    map_bounds: MapBounds | None = None,
) -> str | None:
    mapbox_token = os.environ.get("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("Ошибка: MAPBOX_ACCESS_TOKEN не установлен в .env")
        return None

    base_url = "https://api.mapbox.com/styles/v1/mapbox/light-v11/static"
    url_suffix = f"?access_token={mapbox_token}&attribution=false&logo=false&padding=50"

    # Маркеры
    overlay_parts = []
    marker_color = accent_color.replace("#", "")
    for point in geocoded_points:
        letter = point.name_en[0].lower() if point.name_en else "a"
        overlay_parts.append(
            f"pin-l+{letter}+{marker_color}({point.lon},{point.lat})"
        )

    # Маршруты
    route_parts = []
    point_coords = {p.name: (p.lat, p.lon) for p in geocoded_points}
    for route in map_routes:
        from_c = point_coords.get(route.from_point)
        to_c = point_coords.get(route.to_point)
        if from_c and to_c:
            encoded = polyline.encode([from_c, to_c])
            route_color = route.color_hex.replace("#", "")
            route_parts.append(f"path-4+{route_color}-1({encoded})")

    # Собираем overlay
    all_parts = overlay_parts + route_parts
    overlay_string = ",".join(all_parts)

    # Проверяем длину URL
    full_url = f"{base_url}/{overlay_string}/auto/1280x720@2x.png{url_suffix}"
    if len(full_url) > 8192 and route_parts:
        print("URL слишком длинный — убираем маршруты")
        overlay_string = ",".join(overlay_parts)
        full_url = f"{base_url}/{overlay_string}/auto/1280x720@2x.png{url_suffix}"

    # Если нет точек — используем bounds
    if not overlay_parts:
        if map_bounds:
            bounds_str = f"[{map_bounds.west},{map_bounds.south},{map_bounds.east},{map_bounds.north}]"
            full_url = f"{base_url}/{bounds_str}/1280x720@2x.png{url_suffix}"
        else:
            print("Ошибка: нет ни точек, ни границ")
            return None

    # Скачиваем карту
    try:
        response = requests.get(full_url, stream=True)
        if response.status_code != 200:
            print(f"Mapbox вернул ошибку {response.status_code}: {response.text[:300]}")
            return None

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса к Mapbox: {e}")
        return None


# ─── Главная функция ──────────────────────────────────────────────────
def reverse_map(
    image_path: str,
    accent_color: str,
    output_dir: str,
) -> dict | None:
    print(f"Анализ карты: {image_path}")
    analysis = analyze_map_image(image_path)
    if analysis is None:
        return None

    print(f"Найдено точек: {len(analysis.points)}")
    print(f"Найдено маршрутов: {len(analysis.routes)}")

    geocoded = geocode_points(analysis.points)
    if not geocoded:
        print("Не удалось геокодировать ни одной точки")
        return None

    print(f"Геокодировано: {len(geocoded)} из {len(analysis.points)}")

    output_path = os.path.join(output_dir, "map_regenerated.png")
    result_path = generate_map_image(
        geocoded, analysis.routes, accent_color, output_path, analysis.bounds
    )

    if result_path is None:
        return None

    print(f"Карта сохранена: {result_path}")
    return {
        "map_image_path": result_path,
        "analysis": analysis,
        "geocoded_points": geocoded,
    }


# ─── Тест ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python map_reverse.py <path_to_map_image.jpg> [accent_color]")
        sys.exit(1)

    image_path = sys.argv[1]
    accent_color = sys.argv[2] if len(sys.argv) > 2 else "#0066CC"
    output_dir = os.path.dirname(image_path) or "."

    result = reverse_map(image_path, accent_color, output_dir)

    if result:
        print(f"\nMap generated: {result['map_image_path']}")
        print(f"Points found: {len(result['geocoded_points'])}")
        print(f"Analysis:\n{result['analysis'].model_dump_json(indent=2)}")
    else:
        print("Failed to reverse-engineer map")