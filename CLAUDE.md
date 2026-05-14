# PPTX-AI — Project Bible

## Роль ИИ-ассистента
Ты Senior AI-Архитектор и Python Developer в команде PPTX-AI.
- Сначала **спроси** если задача неоднозначна — не пиши код наугад.
- Код выдаётся **целиком**, не кусками. Точечные правки — только построчно.
- В начале каждого файла: docstring с описанием модуля на русском.
- Экономь токены: никакого лишнего текста вокруг кода.

---

## Стек
- **OS/Env:** Windows, PowerShell
- **Python:** 3.14
- **Libs:** python-pptx, pydantic, Pillow, google-generativeai, requests, opencv-python, numpy, scikit-image, python-dotenv
- **Layout:** `stretchable` (Taffy/Rust bindings) — flex/grid, координаты через `_abs_box()`
- **LLM:** Gemini 2.5 Pro (семантика, сложные задачи) / Gemini 2.5 Flash (верстка, быстрые задачи)

---

## Правила кода (ЗАПРЕЩЕНО НАРУШАТЬ)
1. **Типизация:** type hints на всех функциях (параметры + return).
2. **Логирование:** только `logging.getLogger(__name__)`. `print()` запрещён.
3. **Ошибки:** строгие `try/except` с внятными сообщениями. Пустой `except` запрещён.
4. **Модели:** только Pydantic `BaseModel`. `dataclass` запрещён.
5. **Конфиг:** API ключи только из `.env` через `dotenv`. Хардкод запрещён.
6. **Пути:** только `pathlib.Path`. Строки для путей запрещены.
7. **Константы:** `UPPER_CASE` в начале файла. Глобальные переменные запрещены.
8. **Структура:** один файл = один модуль. Функции до 30 строк. Комментарии только там где логика неочевидна. `import *` запрещён.
9. **Hard Bans:** `MORPH_CLOSE`, `vtracer`, `pypotrace`, `EasyOCR`, `keras-ocr`, `&&` в PowerShell.
10. **Масштабируемость:** Код пишется универсальным — не под конкретный пример или кейс.
    Никаких magic numbers (все цифры → константы в `config.py`).
    Никакой логики завязанной на конкретный слайд, цвет или размер.
    Если параметр может измениться — он должен приходить снаружи (аргумент, конфиг, контракт).
    Думай: "что если слайдов будет 100, колонок 16, или размер изменится на 1920×1080?"

---

## Структура проекта
pptx-ai/
├── agents/                  # AI-агенты (мозг)
│   ├── strategy_director.py
│   ├── semantic_editor.py
│   ├── spatial_architect.py
│   └── inspector.py         # бэклог
│
├── core/                    # Инфраструктура (руки)
│   ├── config.py
│   ├── orchestrator.py
│   ├── prompt_assembler.py
│   ├── layout_engine.py
│   ├── svg_renderer.py
│   ├── llm/
│   │   ├── client.py
│   │   ├── normalize.py
│   │   └── ollama.py
│   └── utils/
│       ├── text_metrics.py
│       └── logger.py
│
├── models/
│   └── contracts.py
│
├── parsers/
│   ├── pptx_parser.py
│   └── slide_renderer.py
│
├── postprocess/
│   ├── pptx_fix.py
│   ├── svg_fix.py
│   └── validator.py         # бэклог
│
├── prompts/
│   ├── strategy_director.md
│   ├── semantic_editor.md
│   ├── spatial_architect.md
│   └── map_classifier.md
│
├── config/
│   ├── core_rules.md
│   ├── card.md
│   ├── patterns.md
│   ├── headers/
│   └── styles/
│
├── assets/fonts/
├── projects/
├── output/
└── main.py

---

## Архитектура v5 — Трёхслойная когнитивная модель
> LLM = мозг. Python = руки. Только Agentic Workflow, никаких монолитных промптов.

### Слой 0 — Semantic Editor (`agents/semantic_editor.py`)
- Модель: **Gemini 2.5 Pro** + Chain of Thought `<thinking>`
- Вход: `ParsedSlide` + скриншот слайда
- Что делает: убирает "воду", выявляет Intent, группирует смыслы, выбирает `recommended_modules`
- Выход: `SemanticSlide` (список `SemanticBlock` с `line_budget`)
- **Не думает о пикселях и дизайне**

### Слой 0.5 — Prompt Assembler (`core/prompt_assembler.py`)
- Чистый Python, без LLM
- Загружает **только** те `.md` из `config/`, которые запросил Semantic Editor
- Выход: строка `design_context` для Spatial Architect

### Слой 1 — Spatial Architect (`agents/spatial_architect.py`)
- Модель: **Gemini 2.5 Flash**
- Вход: `SemanticSlide` + `design_context`
- Мыслит в **12-колоночной сетке**, оперирует **бюджетом строк** (~22-24 на слайд)
- Выход: `LayoutPlanV5` (`GridRow` + `GridBlock`, `col_span`, `height_strategy: hug|fill`)

### Слой 2 — Визуальные модули (`agents/`) — бэклог
- Image Generator, Map Redesigner, Flowchart, Chart, Pattern, Custom Infographic
- Хук для API иконок по `icon_concept`

### Слой 2.5 — Python Validator (`postprocess/validator.py`) — бэклог
- Fast-fail: если `y + height > 720` → ошибка обратно на Слой 1 без LLM

### Слой 3 — AI Inspector (`agents/inspector.py`) — бэклог
- Финальная проверка: семантика сохранена + дизайн соответствует системе

---

## Контракты (`models/contracts.py`)
Единый источник истины. Основные модели:

| Модель | Откуда | Куда |
|---|---|---|
| `ParsedPresentation` / `ParsedSlide` | Parser | Semantic Editor |
| `PresentationStrategy` | Strategy Director | все агенты |
| `SemanticSlide` / `SemanticBlock` | Semantic Editor | Prompt Assembler, Spatial Architect |
| `LayoutPlanV5` / `GridRow` / `GridBlock` | Spatial Architect | Layout Engine |
| `SlideGeometry` / `BlockGeometry` | Layout Engine | SVG Renderer |
| `RenderedText` | Layout Engine | SVG Renderer |
| `DesignedSlide` | SVG Renderer | Orchestrator |

---

## Design System
| Параметр | Значение |
|---|---|
| Слайд | 1280 × 720 px |
| Отступы | 43px гор., 20px верт. |
| Рабочая область | 1194 × 680 px |
| Колонок | 12 |
| Ширина колонки | 72px |
| Gutter | 30px |
| Бюджет строк | ~22-24 строки на слайд |
| Шрифт | Google Sans / Inter (fallback) |
| Акцент по умолчанию | #0066CC |

---

## Таск-трекер

### ✅ Завершено
- Фазы 0-4.4: парсер, контракты, Strategy Director, Vertex AI
- Фаза 4.7: LayoutEngine v5 (stretchable + Pillow, точные метрики текста)
- Фаза 4.7.1: SVG Renderer v5
- Фаза 4.8 (частично): контракты v5, prompt_assembler динамический, orchestrator v5, рефакторинг структуры

### 🔄 В работе — Фаза 4.8: Завершение пайплайна
- [ ] `agents/semantic_editor.py` — Слой 0
- [ ] `agents/spatial_architect.py` — Слой 1

### 📋 Бэклог

**Фаза 5 — Визуальные модули (Слой 2)**
- [ ] API иконок (SVG по `icon_concept`)
- [ ] Chart (нативные графики PPTX)
- [ ] Pattern (SVG-заготовки: SWOT, Timeline и др.)
- [ ] Map Redesigner (cv2 + LLM Vision)

**Фаза 6 — Валидация и QA**
- [ ] `postprocess/validator.py` — Слой 2.5, fast-fail при overflow
- [ ] `agents/inspector.py` — Слой 3, семантика + эстетика

**Фаза 7 — Оптимизация**
- [ ] pytest (цель: 80% слайдов без ручных правок)

## Архитектурная проблема: LayoutPlanV5 ↔ LayoutEngine

`layout_engine.py` принимает старый `LayoutPlan` (RowInstruction/ColumnInstruction).
`orchestrator.py` передаёт новый `LayoutPlanV5` (GridRow/GridBlock).

Два варианта решения (на выбор):
- Вариант A: Адаптер _v5_to_v4() в orchestrator.py — минимальный риск
- Вариант B: Рефакторинг compute_geometry() под LayoutPlanV5 — архитектурно чище

Решение не принято. Обсудить перед кодингом.