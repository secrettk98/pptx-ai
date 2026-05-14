# PPTX-AI — Project Bible

## Роль ИИ-ассистента
Ты Senior AI-Архитектор и Python Developer в команде PPTX-AI.
- Сначала **спроси** если задача неоднозначна — не пиши код наугад.
- Код выдаётся **целиком**, не кусками. Точечные правки — только построчно.
- В начале каждого файла: docstring с описанием модуля на русском.
- Экономь токены: никакого лишнего текста вокруг кода.

### Правила экономии токенов (КРИТИЧНО)
- **НЕ переписывай целый файл** если нужно поменять 1-3 функции. Вместо этого: опиши словами что и где меняется, покажи только изменённые функции.
- **НЕ дублируй код** — если файл уже написан и нужны мелкие правки, давай точечные патчи с указанием строк/функций.
- **Полный файл** выдавай ТОЛЬКО когда: (а) файл новый, (б) меняется >50% кода, (в) пользователь явно попросил.
- Перед написанием кода **спроси подтверждение** на план изменений. Не пиши код без согласия.

---

## Стек
- **OS/Env:** Windows, PowerShell
- **Python:** 3.14
- **Libs:** python-pptx, pydantic, Pillow, google-generativeai, requests, opencv-python, numpy, scikit-image, python-dotenv
- **Layout:** `stretchable` (Taffy/Rust bindings) — flex/grid, координаты через `_abs_box()`
- **LLM:** Gemini 2.5 Pro (семантика, layout) / Gemini 2.5 Flash (классификация, быстрые задачи)

---

## Правила кода (ЗАПРЕЩЕНО НАРУШАТЬ)
1. **Типизация:** type hints на всех функциях (параметры + return).
2. **Логирование:** только `logging.getLogger(__name__)`. `print()` запрещён.
3. **Ошибки:** строгие `try/except` с внятными сообщениями. Пустой `except` запрещён.
4. **Модели:** только Pydantic `BaseModel`. `dataclass` запрещён. Исключение: `@dataclass` для внутренних контейнеров layout_engine (BlockCtx).
5. **Конфиг:** API ключи только из `.env` через `dotenv`. Хардкод запрещён.
6. **Пути:** только `pathlib.Path`. Строки для путей запрещены.
7. **Константы:** `UPPER_CASE` в начале файла. Глобальные переменные запрещены.
8. **Структура:** один файл = один модуль. Функции до 30 строк. Комментарии только там где логика неочевидна. `import *` запрещён.
9. **Hard Bans:** `MORPH_CLOSE`, `vtracer`, `pypotrace`, `EasyOCR`, `keras-ocr`, `&&` в PowerShell.
10. **Масштабируемость:** Код пишется универсальным — не под конкретный пример или кейс.
    Никаких magic numbers (все цифры → константы в `config.py`).
    Никакой логики завязанной на конкретный слайд, цвет или размер.
    Если параметр может измениться — он должен приходить снаружи (аргумент, конфиг, контракт).
    Думай: "что если слайдов будет 100, колонок 16, или размер изменился на 1920×1080?"
11. **Никаких костылей:** Решения должны быть универсальными. Если правка работает только для одного типа слайда — это костыль, переделай. LLM не калькулятор — пиксельные расчёты делает только Python.

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
│   └── validator.py         # В РАБОТЕ — Слой 2.5
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
- Что делает: убирает "воду", выявляет Intent, группирует смыслы
- Выход: `SemanticSlide` (список `SemanticBlock` с `line_budget`)
- **Не думает о пикселях и дизайне**
- **Строго сохраняет все визуальные элементы (chart, visual, table) из оригинала**
- **Никогда не переводит контент — сохраняет язык оригинала**

### Слой 0.5 — Prompt Assembler (`core/prompt_assembler.py`)
- Чистый Python, без LLM
- Загружает **только** те `.md` из `config/`, которые нужны по semantic_type блоков
- `recommended_modules` собирается Python из semantic_type + visual_subtype (не из LLM)
- Выход: строка `design_context` для Spatial Architect

### Слой 1 — Spatial Architect (`agents/spatial_architect.py`)
- Модель: **Gemini 2.5 Pro**
- Вход: `SemanticSlide` (без content — только id, тип, line_budget) + `design_context`
- Мыслит в **12-колоночной сетке** и **пиксельных высотах**
- Выход: `LayoutPlanV5` (`GridRow` + `GridBlock`, `col_span`, `height_strategy`)
- **НЕ получает и НЕ возвращает content** — контент подставляет orchestrator (`_enrich_layout()`)

### Слой 1.5 — Enrich (`core/orchestrator.py` → `_enrich_layout()`)
- Чистый Python, без LLM
- Матчит `GridBlock.block_id` → `SemanticBlock`
- Копирует `content`, `semantic_type`, `visual_subtype` в GridBlock

### Слой 2 — Визуальные модули (`agents/`) — бэклог
- Image Generator, Map Redesigner, Flowchart, Chart, Pattern, Custom Infographic
- Хук для API иконок по `icon_concept`

### Слой 2.5 — Python Validator (`postprocess/validator.py`) — В РАБОТЕ
- Прогоняет LayoutPlanV5 через layout_engine.compute_geometry()
- Если блок вылезает за границы (y + h > 700) → формирует текстовый feedback
- Отправляет feedback обратно в Spatial Architect
- Максимум MAX_VALIDATOR_RETRIES попыток, потом берёт лучший вариант
- **LLM не калькулятор** — пиксельную валидацию делает только Python

### Слой 3 — AI Inspector (`agents/inspector.py`) — бэклог
- Финальная проверка: семантика сохранена + дизайн соответствует системе

---

## Контракты (`models/contracts.py`)
Единый источник истины. v4-модели (ColumnInstruction, RowInstruction, LayoutPlan) удалены.

| Модель | Откуда | Куда |
|---|---|---|
| `ParsedPresentation` / `ParsedSlide` | Parser | Semantic Editor |
| `PresentationStrategy` | Strategy Director | все агенты |
| `SemanticSlide` / `SemanticBlock` | Semantic Editor | Prompt Assembler, Orchestrator |
| `LayoutPlanV5` / `GridRow` / `GridBlock` | Spatial Architect + Enrich | Validator, Layout Engine |
| `SlideGeometry` / `BlockGeometry` | Layout Engine | SVG Renderer |
| `RenderedText` | Layout Engine | SVG Renderer |
| `DesignedSlide` | SVG Renderer | Orchestrator |

### GridBlock — разделение ответственности
- **LLM заполняет:** block_id, col_start, col_span, height_strategy, render
- **Python заполняет (enrich):** semantic_type, content, visual_subtype

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

## Пайплайн (порядок вызовов в orchestrator.py)
1. Parser → ParsedPresentation + JPG скриншоты
2. Strategy → PresentationStrategy (один раз на всю презентацию)
3. Per slide: 3a. Semantic Editor → SemanticSlide 3b. Prompt Assembler → design_context (строка) 3c. Spatial Architect → LayoutPlanV5 (без content) 3d. Enrich → LayoutPlanV5 (с content) 3e. Validator → OK или feedback → retry 3c-3d (макс. N раз) 3f. Layout Engine → SlideGeometry (точные пиксели) 3g. SVG Renderer → DesignedSlide (SVG код)
Copy

---

## Таск-трекер

### ✅ Завершено
- Фазы 0-4.4: парсер, контракты, Strategy Director, Vertex AI
- Фаза 4.7: LayoutEngine v5 (stretchable + Pillow, точные метрики текста)
- Фаза 4.7.1: SVG Renderer v5
- Фаза 4.8: контракты v5 (чистые, без v4), prompt_assembler, orchestrator v5 с enrich, рефакторинг layout_engine под LayoutPlanV5/GridRow/GridBlock
- Фаза 4.8.1: semantic_editor.py, spatial_architect.py — агенты написаны
- Фаза 4.8.2: промпты semantic_editor.md и spatial_architect.md обновлены (HEIGHT AWARENESS, COMPOSITION PATTERNS, правильные content schema)

### 🔄 В работе — Фаза 4.9: Validator (Слой 2.5)
- [ ] `postprocess/validator.py` — overflow detection + feedback loop
- [ ] `agents/spatial_architect.py` — добавить параметр `feedback: str | None`
- [ ] `core/orchestrator.py` — цикл retry: Architect → Enrich → Validate → (retry или Engine)
- [ ] Промпт `semantic_editor.md` — мелкие правки: сохранение визуалов, запрет перевода, line_budget для chart/visual

### 📋 Бэклог

**Фаза 5 — Визуальные модули (Слой 2)**
- [ ] API иконок (SVG по `icon_concept`)
- [ ] Chart (нативные графики PPTX)
- [ ] Pattern (SVG-заготовки: SWOT, Timeline и др.)
- [ ] Map Redesigner (cv2 + LLM Vision)

**Фаза 6 — QA**
- [ ] `agents/inspector.py` — Слой 3, семантика + эстетика

**Фаза 7 — Оптимизация**
- [ ] pytest (цель: 80% слайдов без ручных правок)

---

## Известные проблемы и решения

### Overflow (контент не влезает в слайд)
- **Причина:** LLM не умеет точно считать пиксели
- **Решение:** Validator (Слой 2.5) — Python считает реальные размеры, при overflow даёт feedback Architect-у
- **НЕ решение:** костыли в промптах типа "убери карточки если не влезает"

### Разные margins
- **Причина:** content_root с justify_content=FLEX_START + все блоки hug → контент прижат к верху
- **Решение:** Architect должен назначать fill нижнему контентному ряду. Validator поможет итеративно.

### svg_renderer: col_id → block_id
- Заменить `bl.col_id` на `bl.block_id` в комментарии внутри render_slide()