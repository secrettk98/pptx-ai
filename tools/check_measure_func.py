"""Проверка: stretchable умеет звать наш measure_func для листовых узлов.

Сценарий: контейнер 400×AUTO, внутри 1 текстовый узел с измерителем.
Ожидаем, что высота контейнера = высота текста при ширине 400.
"""

import sys
from math import isnan
from stretchable import Node, Edge
from stretchable.style import AUTO
from stretchable.style.geometry.size import SizePoints
from stretchable.style.geometry.length import Scale

sys.path.insert(0, ".")
from core.text_metrics import measure_block


TEXT = (
    "Это длинный текст для проверки measure_func в stretchable. "
    "Движок должен спросить нас о высоте при заданной ширине, "
    "и мы вернём реальную высоту по метрикам Inter."
)


def my_measure(node, known_dimensions, available_space):
    """Callback от stretchable.
    
    known_dimensions: SizePoints — известные размеры от родителя (width/height = LengthPoints с .value, .value может быть NaN).
    available_space: SizeAvailableSpace — доступное место (width/height = LengthAvailableSpace; scale=POINTS/MIN_CONTENT/MAX_CONTENT).
    
    Возвращает: SizePoints(width, height) в pt.
    """
    kw_v = known_dimensions.width.value
    aw = available_space.width

    if not isnan(kw_v):
        # Родитель уже задал ширину — используем её
        w_constraint = float(kw_v)
    elif aw.scale == Scale.POINTS and not isnan(aw.value):
        # Конечное доступное место
        w_constraint = float(aw.value)
    else:
        # MIN_CONTENT → самая длинная "неделимая" единица (для текста — самое широкое слово)
        # MAX_CONTENT → текст в одну строку. Для простоты теста — используем 400.
        w_constraint = 400.0

    print(f"    [measure] known.w={kw_v} avail.w=({aw.scale.name}, {aw.value}) → constraint={w_constraint}")

    actual_w, actual_h, lines = measure_block(TEXT, w_constraint, size_pt=12)
    print(f"    → {actual_w:.1f} × {actual_h:.1f} ({len(lines)} строк)")
    return SizePoints(width=actual_w, height=actual_h)


def main():
    # Контейнер фиксированной ширины, высота auto — пусть растёт по контенту
    container = Node(size=(400, AUTO), padding=10)

    # Листовой узел с measure_func
    leaf = Node(
        size=(AUTO, AUTO),
        measure=my_measure,
    )
    container.add(leaf)

    print("compute_layout()...")
    container.compute_layout()

    cb = container.get_box(Edge.BORDER)
    lb = leaf.get_box(Edge.BORDER)

    print(f"\nКонтейнер: x={cb.x:.1f} y={cb.y:.1f} w={cb.width:.1f} h={cb.height:.1f}")
    print(f"Лист:      x={lb.x:.1f} y={lb.y:.1f} w={lb.width:.1f} h={lb.height:.1f}")
    print(f"\nОжидаем: контейнер w=400, h ≈ высота_текста + 20 (padding 10+10)")


if __name__ == "__main__":
    main()