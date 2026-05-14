"""Точное измерение текста через Pillow + TTF.

Зачем: word-wrap, расчёт высоты текстовых блоков, обрезка с многоточием.
Все размеры — в пикселях SVG (1pt ≈ 1.333px при 96 DPI).

Использование:
    from core.text_metrics import measure, wrap, fit_height

    w = measure("Привет, мир", size_pt=12)            # ширина строки в px
    lines = wrap("Длинный текст...", max_w=300, size_pt=12)  # список строк
    h = fit_height(lines, size_pt=12)                 # высота блока в px
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

logger = logging.getLogger(__name__)

# ── Константы ────────────────────────────────────────────────
PT_TO_PX = 96 / 72                  # 1pt = 1.333px при 96 DPI
LINE_HEIGHT_FACTOR = 1.35           # межстрочный интервал по умолчанию

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Системные фолбэки (Windows). Используются если Inter не найден.
SYSTEM_FALLBACKS = {
    "regular": ["C:/Windows/Fonts/arial.ttf", "arial.ttf"],
    "bold":    ["C:/Windows/Fonts/arialbd.ttf", "arialbd.ttf"],
}

FONT_FILES = {
    "regular": FONTS_DIR / "Inter-Regular.ttf",
    "bold":    FONTS_DIR / "Inter-Bold.ttf",
}


# ── Загрузка шрифтов с кэшем ─────────────────────────────────

@lru_cache(maxsize=64)
def _font(weight: str, size_pt: float) -> ImageFont.FreeTypeFont:
    """Возвращает Pillow-шрифт. weight: 'regular' | 'bold'."""
    px = max(1, int(round(size_pt * PT_TO_PX)))

    path = FONT_FILES.get(weight)
    if path and path.exists():
        try:
            return ImageFont.truetype(str(path), size=px)
        except Exception as e:
            logger.warning(f"Не удалось загрузить {path}: {e}")

    for fb in SYSTEM_FALLBACKS.get(weight, []):
        try:
            return ImageFont.truetype(fb, size=px)
        except Exception:
            continue

    logger.error(f"Шрифт '{weight}' не найден, использую default")
    return ImageFont.load_default()


# ── Измерение ────────────────────────────────────────────────

def measure(text: str, size_pt: float = 12, bold: bool = False) -> float:
    """Ширина строки в пикселях. Многострочный текст не поддерживается."""
    if not text:
        return 0.0
    f = _font("bold" if bold else "regular", size_pt)
    return float(f.getlength(str(text)))


def line_height(size_pt: float = 12, factor: float = LINE_HEIGHT_FACTOR) -> float:
    """Высота одной строки в пикселях."""
    return size_pt * PT_TO_PX * factor

def baseline_offset(size_pt: float = 12, bold: bool = False) -> float:
    """Смещение baseline от верхнего края строки в пикселях.
    
    Pillow font.getmetrics() → (ascent, descent).
    ascent — расстояние от baseline до верха глифов.
    Это и есть наш offset: рисуем текст на y + ascent.
    """
    f = _font("bold" if bold else "regular", size_pt)
    ascent, _ = f.getmetrics()
    return float(ascent)


# ── Word-wrap ────────────────────────────────────────────────

def _break_long_word(word: str, max_w: float, size_pt: float, bold: bool) -> list[str]:
    """Жёстко режет слово, которое не влезает по ширине."""
    parts: list[str] = []
    cur = ""
    for ch in word:
        if measure(cur + ch, size_pt, bold) <= max_w or not cur:
            cur += ch
        else:
            parts.append(cur)
            cur = ch
    if cur:
        parts.append(cur)
    return parts


def wrap(
    text: str,
    max_w: float,
    size_pt: float = 12,
    bold: bool = False,
) -> list[str]:
    """Перенос текста по реальной пиксельной ширине.

    Уважает \\n в исходном тексте (явные переносы абзаца).
    Слова длиннее max_w режутся по символам.
    """
    if not text:
        return []

    out: list[str] = []
    for paragraph in str(text).split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            out.append("")
            continue

        cur = ""
        for word in paragraph.split():
            test = f"{cur} {word}".strip()
            if measure(test, size_pt, bold) <= max_w:
                cur = test
                continue

            if cur:
                out.append(cur)
                cur = ""

            if measure(word, size_pt, bold) > max_w:
                parts = _break_long_word(word, max_w, size_pt, bold)
                out.extend(parts[:-1])
                cur = parts[-1] if parts else ""
            else:
                cur = word

        if cur:
            out.append(cur)

    return out


def fit_height(
    lines: list[str],
    size_pt: float = 12,
    line_factor: float = LINE_HEIGHT_FACTOR,
) -> float:
    """Высота блока из N строк в пикселях."""
    if not lines:
        return 0.0
    return len(lines) * line_height(size_pt, line_factor)


def measure_block(
    text: str,
    max_w: float,
    size_pt: float = 12,
    bold: bool = False,
    line_factor: float = LINE_HEIGHT_FACTOR,
) -> tuple[float, float, list[str]]:
    """Удобный шорткат: возвращает (ширина_фактическая, высота, строки).

    ширина_фактическая = max(ширина_строк) — может быть < max_w.
    """
    lines = wrap(text, max_w, size_pt, bold)
    if not lines:
        return 0.0, 0.0, []
    w = max((measure(ln, size_pt, bold) for ln in lines), default=0.0)
    h = fit_height(lines, size_pt, line_factor)
    return w, h, lines


def truncate(text: str, max_w: float, size_pt: float = 12, bold: bool = False) -> str:
    """Однострочная обрезка с многоточием."""
    text = str(text)
    if measure(text, size_pt, bold) <= max_w:
        return text

    ell = "…"
    ell_w = measure(ell, size_pt, bold)
    if ell_w > max_w:
        return ""

    out = ""
    for ch in text:
        if measure(out + ch, size_pt, bold) + ell_w > max_w:
            break
        out += ch
    return out + ell


# ── Smoke-test ───────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"\nFonts dir: {FONTS_DIR}")
    print(f"Inter-Regular: {'OK' if FONT_FILES['regular'].exists() else 'НЕТ — будет fallback'}")
    print(f"Inter-Bold:    {'OK' if FONT_FILES['bold'].exists() else 'НЕТ — будет fallback'}")

    print("\n── measure() ─────────────────────────────")
    for t in ["AI", "Hello world", "Привет, мир", "Финансовые показатели"]:
        print(f"  '{t}' → {measure(t, 12):.1f}px (12pt regular)")
        print(f"  '{t}' → {measure(t, 12, bold=True):.1f}px (12pt bold)")

    print("\n── wrap() при max_w=200px, 12pt ──────────")
    long_text = (
        "Это длинный текст для проверки word-wrap движка. "
        "Он должен корректно переноситься по словам и считать ширину "
        "по реальным метрикам шрифта Inter."
    )
    lines = wrap(long_text, 200, 12)
    for i, ln in enumerate(lines, 1):
        print(f"  {i}: '{ln}' ({measure(ln, 12):.1f}px)")

    print("\n── measure_block() ───────────────────────")
    w, h, _ = measure_block(long_text, 200, 12)
    print(f"  фактич. ширина={w:.1f}px, высота={h:.1f}px, строк={len(lines)}")

    print("\n── truncate() ────────────────────────────")
    print(f"  '{truncate(long_text, 150, 12)}'")
    print(f"  '{truncate(long_text, 50, 12)}'")

    print("\n✅ text_metrics готов к использованию.")