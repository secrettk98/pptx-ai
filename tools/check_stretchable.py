"""Проверка: stretchable + Pillow работают на этой машине."""

import sys
import platform


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── 0. Окружение ─────────────────────────────────────────────
section("0. Окружение")
print(f"Python:   {sys.version}")
print(f"Platform: {platform.platform()}")


# ── 1. stretchable ───────────────────────────────────────────
section("1. stretchable — flex layout")

try:
    from stretchable import Node, Edge
    from stretchable.style import PCT, AUTO
    from stretchable.style.core import FlexDirection
    print("✅ Импорт stretchable OK")
except Exception as e:
    print(f"❌ Импорт stretchable FAILED: {e}")
    sys.exit(1)

# Слайд 1280×720, два блока в ряд с gap=26 и padding=20
try:
    slide = Node(size=(1280, 720), padding=20)

    row = Node(
        flex_direction=FlexDirection.ROW,
        gap=26,
        flex_grow=1,
    )
    card1 = Node(flex_grow=1, size=(AUTO, 200))
    card2 = Node(flex_grow=1, size=(AUTO, 200))
    row.add(card1, card2)
    slide.add(row)

    slide.compute_layout()

    b1 = card1.get_box(Edge.BORDER)
    b2 = card2.get_box(Edge.BORDER)
    print(f"✅ Layout посчитан")
    print(f"   card1: x={b1.x:.1f} y={b1.y:.1f} w={b1.width:.1f} h={b1.height:.1f}")
    print(f"   card2: x={b2.x:.1f} y={b2.y:.1f} w={b2.width:.1f} h={b2.height:.1f}")
    print(f"   (ожидаем: w≈607, y=20, x=20 и x≈653)")
except Exception as e:
    print(f"❌ Layout FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ── 2. Pillow — измерение текста ─────────────────────────────
section("2. Pillow — text metrics")

try:
    from PIL import ImageFont, __version__ as pil_v
    print(f"✅ Pillow {pil_v}")
except Exception as e:
    print(f"❌ Импорт Pillow FAILED: {e}")
    sys.exit(1)

candidates = ["arial.ttf", "Arial.ttf", "C:/Windows/Fonts/arial.ttf"]
font = None
for c in candidates:
    try:
        font = ImageFont.truetype(c, size=16)
        print(f"✅ Шрифт найден: {c}")
        break
    except Exception:
        continue

if not font:
    print("⚠️  Системный Arial не найден — используем default")
    font = ImageFont.load_default()

samples = [
    "Hello",
    "Привет, мир",
    "Финансовые показатели за квартал",
    "AI",
]
for s in samples:
    try:
        w = font.getlength(s)
        print(f"   '{s}' → {w:.1f}px (font=16pt)")
    except Exception as e:
        print(f"   '{s}' → ОШИБКА: {e}")


# ── Итог ─────────────────────────────────────────────────────
section("ИТОГ")
print("✅ Оба движка работают. Можно идти дальше — Шаг 2.")