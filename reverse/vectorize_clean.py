"""
Векторизация v4: напрямую с оригинальной карты.
HSV фильтрация (S>=80) убирает подложку → Skan → SVG
"""
import cv2
import numpy as np
from pathlib import Path
from skimage.morphology import skeletonize
from skan import Skeleton

INPUT = "projects/test_map/slide_map.jpg"
OUTPUT_DIR = Path("projects/test_map/vectors_v4")
OUTPUT_DIR.mkdir(exist_ok=True)

COLORS = {
    "green_routes": {
        "lower": np.array([35, 80, 50]),
        "upper": np.array([85, 255, 255]),
        "stroke": "#2E7D32",
        "width": 3,
    },
    "blue_routes": {
        "lower": np.array([90, 60, 50]),
        "upper": np.array([130, 255, 255]),
        "stroke": "#1565C0",
        "width": 2,
    },
}

EPSILON_FACTOR = 0.02

def simplify_branch(points, epsilon_factor):
    if len(points) < 3:
        return points
    pts = points.reshape(-1, 1, 2).astype(np.float32)
    length = cv2.arcLength(pts, closed=False)
    epsilon = epsilon_factor * length
    approx = cv2.approxPolyDP(pts, epsilon, closed=False)
    return approx.reshape(-1, 2)

img = cv2.imread(INPUT)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
h, w = img.shape[:2]
svg_lines = []

for name, cfg in COLORS.items():
    print(f"\n--- {name} ---")

    mask = cv2.inRange(hsv, cfg["lower"], cfg["upper"])

    # Агрессивное закрытие дыр от текста
    kernel_close = np.ones((15, 15), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

    # Убираем мелкий мусор
    kernel_open = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)

    cv2.imwrite(str(OUTPUT_DIR / f"mask_{name}.png"), mask)

    # Скелет
    binary = (mask > 0).astype(np.uint8)
    skel = skeletonize(binary)

    if skel.sum() == 0:
        print("  Пусто")
        continue

    # Skan
    sk = Skeleton(skel)
    branch_count = 0

    for i in range(sk.n_paths):
        coords = sk.path_coordinates(i)
        if len(coords) < 10:
            continue

        points = coords[:, ::-1].copy()
        simple = simplify_branch(points, EPSILON_FACTOR)
        branch_count += 1

        pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in simple)
        svg_lines.append(
            f'  <polyline points="{pts_str}" '
            f'fill="none" stroke="{cfg["stroke"]}" '
            f'stroke-width="{cfg["width"]}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    print(f"  Ветвей: {branch_count}")

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
    + "\n".join(svg_lines)
    + "\n</svg>"
)

svg_path = OUTPUT_DIR / "map_direct_v4.svg"
svg_path.write_text(svg)
print(f"\nГотово: {svg_path}")