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
- **Function calling:** Gemini native tool use для точных измерений текста/таблиц из LLM

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
11. **Никаких костылей:** Решения должны быть универсальными. Если правка работает только для одного типа слайда — это костыль, переделай. LLM не калькулятор — пиксельные расчёты делает только Python (или Python через tool use из LLM).

---

## Структура проекта
```
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
│   │   ├── tools.py         # НОВЫЙ — реестр tools для function calling
│   │   └── ollama.py
│   └── utils/
│       ├── text_metrics.py
│       ├── grid_visualizer.py  # НОВЫЙ — рендер пустой сетки 12×27 для промпта
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
│   └── debug/               # дампы попыток валидатора по слайдам
└── main.py
```

---

## Архитектура v5 — Трёхслойная когнитивная модель
> LLM = мозг. Python = руки. Только Agentic Workflow.
> LLM умеет **звать Python через tools** — это не нарушает принцип, а усиливает его: LLM думает, Python считает.

### Слой 0 — Semantic Editor (`agents/semantic_editor.py`)
- Модель: **Gemini 2.5 Pro** + Chain of Thought `<thinking>` + **Tool Use**
- Вход: `ParsedSlide` + скриншот слайда + design_context
- Что делает:
  1. Убирает "воду", выявляет Intent, группирует смыслы
  2. **Накидывает черновой layout** — proposed_col_span на каждый блок по минимальным правилам
  3. **Меряет текст и таблицы через tool** `measure_texts_batch` — получает точный `height_cells`
  4. Для `chart` / `visual` / `image` высоту считает сам (chart — гибко в диапазоне, visual — по aspect_ratio)
  5. Проверяет суммарный budget ≤ 27 клеток через tool `check_total_budget`. При overflow — компрессирует контент (сокращает текст, понижает priority) и пере-меряет.
- Выход: `SemanticSlide` (список `SemanticBlock` с `proposed_col_span` и точным `height_cells`)
- **Строго сохраняет все визуальные элементы (chart, visual, table) из оригинала**
- **Никогда не переводит контент — сохраняет язык оригинала**
- **Минимизирует tool calls** — один батч-вызов на все текстовые блоки, не по одному

#### Минимальные правила чернового layout (для Semantic)
| Кол-во контентных блоков (без heading) | Рекомендация по ширине |
|---|---|
| 1 | 12 колонок (full-width) |
| 2 | 6 + 6 |
| 3 | 4 + 4 + 4 |
| 4 | 6+6 в две строки, или 3+3+3+3 |
| heading | всегда 12 колонок отдельной строкой |

Это **дефолт**. LLM может отклониться при веской причине (например, visual шире текста: 8+4).

### Слой 0.5 — Prompt Assembler (`core/prompt_assembler.py`)
- Чистый Python, без LLM
- Загружает **только** те `.md` из `config/`, которые нужны по semantic_type блоков
- `recommended_modules` собирается Python из semantic_type + visual_subtype (не из LLM)
- Выход: строка `design_context` для Spatial Architect

### Слой 1 — Spatial Architect (`agents/spatial_architect.py`)
- Модель: **Gemini 2.5 Pro** + multimodal (получает PNG пустой сетки в промпт)
- Вход: `SemanticSlide` (без content — только id, тип, **точный `height_cells`**, `proposed_col_span`) + `design_context` + PNG сетки 12×27 + `feedback: str | None`
- Мыслит в **сетке 12×27 клеток** (не в пикселях!)
- Получает уже готовые размеры от Semantic — не угадывает высоту
- Финализирует композицию: `row_start_cell`, `col_start`, `col_span`, выравнивание, gap'ы
- Может **перераспределить колонки** (например 6+6 вместо 4+8) — но тогда Validator пере-меряет текст через tool
- Выход: `LayoutPlanV5` (`GridRow` + `GridBlock` с `row_start_cell`, `col_start`, `col_span`, `height_cells`)
- **НЕ получает и НЕ возвращает content** — контент подставляет orchestrator (`_enrich_layout()`)

### Слой 1.5 — Enrich (`core/orchestrator.py` → `_enrich_layout()`)
- Чистый Python, без LLM
- Матчит `GridBlock.block_id` → `SemanticBlock`
- Копирует `content`, `semantic_type`, `visual_subtype` в GridBlock

### Слой 2 — Визуальные модули (`agents/`) — бэклог
- Image Generator, Map Redesigner, Flowchart, Chart, Pattern, Custom Infographic
- Хук для API иконок по `icon_concept`

### Слой 2.5 — Python Validator (`postprocess/validator.py`) — В РАБОТЕ
- Прогоняет LayoutPlanV5 через layout_engine на уровне **клеток** (не пикселей!)
- Проверки:
  - **Overflow вертикальный:** сумма `height_cells` по строкам > `GRID_ROWS` (27)
  - **Overflow горизонтальный:** `col_start + col_span` > `GRID_COLS` (12)
  - **Overlap:** пересечения блоков в матрице 12×27
  - **Negative coords:** `col_start < 0` или `row_start_cell < 0`
- Если Architect изменил `col_span` относительно `proposed_col_span` → пере-меряет текст через тот же tool `measure_texts_batch`
- Penalty score (веса в config.py):
  - `overflow_cells × OVERFLOW_PENALTY_PER_CELL` (default 1.0)
  - `overlap_count × OVERLAP_PENALTY` (default 100.0)
  - `negative_count × NEGATIVE_COORD_PENALTY` (default 50.0)
- Формирует текстовый feedback → отправляет Spatial Architect-у
- Максимум `MAX_VALIDATOR_RETRIES` попыток (default 2), потом берёт **лучший вариант** по минимальному penalty
- Дампит все попытки в `output/debug/slide_{N}/attempt_{M}.json` + финальный `chosen.json`
- **LLM не калькулятор** — валидацию делает только Python

### Слой 3 — AI Inspector (`agents/inspector.py`) — бэклог
- Финальная проверка: семантика сохранена + дизайн соответствует системе

---

## Tool Use — реестр tools для Gemini (`core/llm/tools.py`)

### Доступные tools для Semantic Editor
| Tool | Назначение | Аргументы | Возврат |
|---|---|---|---|
| `measure_texts_batch` | Точная высота текста и таблиц в клетках | `items: list[{block_id, text, style, width_cols}]` | `dict[block_id, height_cells]` |
| `check_total_budget` | Проверка суммарной высоты vs 27 клеток | `blocks: list[{block_id, height_cells}]` | `{total, fits, overflow_cells}` |

### Принципы tool use
1. **Минимум round-trips:** один батч-вызов на все блоки, не по одному
2. **Только для текста и таблиц:** chart/visual/image LLM считает сама по правилам
3. **Лимит вызовов:** `MAX_TOOL_CALLS_PER_SLIDE = 5` в config — защита от бесконечного цикла
4. **Логирование:** каждый tool call логируется через `logging.getLogger(__name__)`

---

## Контракты (`models/contracts.py`)
Единый источник истины. v4-модели удалены.

| Модель | Откуда | Куда |
|---|---|---|
| `ParsedPresentation` / `ParsedSlide` | Parser | Semantic Editor |
| `PresentationStrategy` | Strategy Director | все агенты |
| `SemanticSlide` / `SemanticBlock` | Semantic Editor | Prompt Assembler, Spatial Architect, Orchestrator |
| `LayoutPlanV5` / `GridRow` / `GridBlock` | Spatial Architect + Enrich | Validator, Layout Engine |
| `SlideGeometry` / `BlockGeometry` | Layout Engine | SVG Renderer |
| `RenderedText` | Layout Engine | SVG Renderer |
| `DesignedSlide` | SVG Renderer | Orchestrator |

### SemanticBlock — ключевые поля
- `block_id`, `semantic_type`, `visual_subtype`
- `content` (сырой текст/данные)
- `priority` (важность для компрессии при overflow)
- `proposed_col_span: int` — черновая ширина от Semantic (1-12)
- `height_cells: int` — **точная высота в клетках**, измерена через tool или посчитана LLM
- **Удалено:** `line_budget` (заменено на `height_cells`)

### GridBlock — разделение ответственности
- **LLM (Architect) заполняет:** `block_id`, `row_start_cell`, `col_start`, `col_span`, `height_cells`, `render`
- **Python (enrich) заполняет:** `semantic_type`, `content`, `visual_subtype`
- **Удалено:** `height_strategy` (fill/hug) — заменено на явный `height_cells`

### GridRow — ключевые поля
- `row_id`, `row_start_cell: int`, `height_cells: int`, `blocks: list[GridBlock]`

---

## Design System
| Параметр | Значение |
|---|---|
| Слайд | 1280 × 720 px |
| Отступы слайда | 43px гор., 20px верт. |
| layout_canvas (рабочая область для LLM) | 1196 × 676 px |
| **Сетка** | **12 колонок × 27 строк** |
| Размер клетки | ~99.6 × 25 px |
| Gap между рядами | 1 клетка (~25 px), фиксированный |
| Шрифт | Google Sans / Inter (fallback) |
| Акцент по умолчанию | #0066CC |

### Почему сетка 12×27 клеток
- LLM плохо считает пиксели — но хорошо мыслит дискретными клетками
- Меньшая разрядность (1-27 вместо 1-676) = меньше ошибок выбора
- Визуальная подсказка: PNG пустой сетки рендерится динамически через `grid_visualizer.py` и подаётся Architect-у в multimodal промпт
- Вертикальное центрирование автоматическое: если контент = 16 клеток из 27, padding = (27-16)/2 = 5.5 клеток сверху и снизу

---

## Пайплайн (порядок вызовов в orchestrator.py)
1. Parser → ParsedPresentation + JPG скриншоты
2. Strategy → PresentationStrategy (один раз на всю презентацию)
3. Per slide:
   - 3a. **Semantic Editor** (с tool use) → SemanticSlide с точными `height_cells` и `proposed_col_span`
   - 3b. Prompt Assembler → design_context (строка)
   - 3c. **Spatial Architect** (с PNG сетки + feedback) → LayoutPlanV5 (без content)
   - 3d. Enrich → LayoutPlanV5 (с content)
   - 3e. **Validator** → OK или feedback → retry 3c-3d (макс. `MAX_VALIDATOR_RETRIES`), либо лучший вариант по penalty
   - 3f. Layout Engine → SlideGeometry (конвертация клетки → пиксели)
   - 3g. SVG Renderer → DesignedSlide (SVG код)

---

## Таск-трекер

### ✅ Завершено
- Фазы 0-4.4: парсер, контракты, Strategy Director, Vertex AI
- Фаза 4.7: LayoutEngine v5 (stretchable + Pillow, точные метрики текста)
- Фаза 4.7.1: SVG Renderer v5
- Фаза 4.8: контракты v5, prompt_assembler, orchestrator v5 с enrich, рефакторинг layout_engine под LayoutPlanV5/GridRow/GridBlock
- Фаза 4.8.1: semantic_editor.py, spatial_architect.py — агенты написаны
- Фаза 4.8.2: промпты semantic_editor.md и spatial_architect.md обновлены
- **Фаза 4.9: Сетка клеток 12×27 + Validator** ✅
  - `core/config.py` — добавлены `GRID_COLS=12`, `GRID_ROWS=27`, `CELL_WIDTH≈99.67`, `CELL_HEIGHT≈25.04`, `ROW_GAP_CELLS=1`, `MAX_VALIDATOR_RETRIES=2`, `MAX_TOOL_CALLS_PER_SLIDE=5`, веса penalty (`OVERFLOW_PENALTY_PER_CELL=1.0`, `OVERLAP_PENALTY=100.0`, `NEGATIVE_COORD_PENALTY=50.0`), `DEBUG_DIR`. Уточнены `SLIDE_MARGIN_X=42`, `SLIDE_MARGIN_Y=22` → `WORKING_AREA=1196×676`. Старые `COLUMN_WIDTH`/`GUTTER` помечены DEPRECATED.
  - `models/contracts.py` — `SemanticBlock`: добавлены `priority`, `proposed_col_span`, `height_cells`; удалён `line_budget`. `GridBlock`: добавлены `row_start_cell`, `height_cells`; удалён `height_strategy`. `GridRow`: `row_start_cell` + `height_cells` вместо `row_lines`. `LayoutPlanV5.total_height_cells` вместо `total_lines`. `SemanticSlide.total_height_cells`.
  - `core/layout_engine.py` — полная переписка под absolute-позиционирование: каждый блок — независимое stretchable-дерево с фиксированным размером `(col_span × CELL_WIDTH, height_cells × CELL_HEIGHT)`. Удалены `_compact`, `_set_compact_mode`, `_gap()`, `_flex_grow_for()`, `_build_row()`, `_build_slide_tree()`, `_abs_box()`, header/footer-логика. Добавлено авто-центрирование `_compute_auto_shift_cells()` — если Architect прижал контент к верху и есть запас, все ряды сдвигаются на `(GRID_ROWS - max_bottom) // 2` клеток вниз.
  - `core/utils/grid_visualizer.py` — новый. Рендерит PNG пустой сетки 12×27 (масштаб ×2 → 2392×1352 px) с нумерацией колонок и строк. Кэширует в `TEMP_DIR/grid_12x27_2392x1352.png`. Имя содержит размерность → автоматический сброс кэша при изменении констант. Экспортирует `get_grid_image_path()` и `get_grid_image_bytes()`.
  - `postprocess/validator.py` — новый. Проверки: negative coords, horizontal overflow (`col_start + col_span > 12`), vertical overflow (`max(row_start + height) > 27`), overlap (матрица 12×27 с подсчётом пар пересекающихся блоков). Penalty по весам из config. `validate()` дампит каждую попытку в `output/debug/slide_NNN/attempt_NN.json`. `dump_chosen()` для финального плана. `ValidationResult.changed_col_spans` — словарь блоков, у которых Architect изменил ширину относительно `proposed_col_span` (для пере-измерения в Фазе 4.9.2).
  - `agents/spatial_architect.py` — добавлен параметр `feedback: Optional[str] = None`. PNG сетки передаётся в `call_llm()` через `image_path`. `_build_blocks_summary()` отдаёт только метаданные (без content): `block_id`, `semantic_type`, `visual_subtype`, `priority`, `proposed_col_span`, `height_cells`. Парсинг адаптирован под `row_start_cell` и `height_cells`.
  - `prompts/spatial_architect.md` — полностью переписан под клетки: все пиксельные референсы убраны, явные правила (sum(col_span)=12, 1-cell gap между рядами, max_bottom ≤ 27), workflow в `<thinking>` под клеточную геометрию, output format с `row_start_cell` и `height_cells`.
  - `core/orchestrator.py` — добавлена функция `_design_with_retry()` — цикл Architect → Enrich → Validate с feedback (до `MAX_VALIDATOR_RETRIES + 1` попыток, иначе лучший по penalty). `_enrich_layout()` обрабатывает спейсеры (`block_id` начинается с `spacer_`) тихо без warning. Невалидные планы не кэшируются.

### 🔄 В работе

**Фаза 4.9.1 — Tool use инфраструктура** (СЛЕДУЮЩЕЕ)
- [ ] `core/llm/tools.py` — **новый**, реестр tools (`measure_texts_batch`, `check_total_budget`)
- [ ] `core/llm/client.py` — поддержка function calling loop для Gemini (лимит `MAX_TOOL_CALLS_PER_SLIDE=5`)
- [ ] `core/utils/text_metrics.py` — функция `measure_in_cells(text, width_cols, style)` поверх существующих метрик

**Фаза 4.9.2 — Semantic Editor с tool use + черновой layout**
- [ ] `agents/semantic_editor.py` — интеграция tool use, генерация `proposed_col_span` по минимальным правилам, удаление `line_budget`
- [ ] `prompts/semantic_editor.md` — переписать: минимальные правила layout, инструкции по tool use, правила для chart/visual
- [ ] `core/orchestrator.py` — в `_design_with_retry()` подключить пере-измерение через tool при `result.changed_col_spans` непустом (сейчас только warning)

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
- **Причина:** LLM плохо считает пиксели и не знала точную ширину блока на этапе семантики
- **Решение трёхуровневое:**
  1. **Semantic Editor** меряет текст через tool `measure_texts_batch` ещё до Architect → outputs точный `height_cells`
  2. **Сетка 12×27 клеток** вместо пикселей → LLM мыслит дискретно, ошибок меньше на порядок
  3. **Validator** ловит остаточные ошибки и даёт feedback Architect-у (макс 2 retry)
- **НЕ решение:** костыли в промптах типа "убери карточки если не влезает"

### "Курица и яйцо" между Semantic и Architect
- **Причина:** Semantic не знал ширину блока, Architect не знал реальную высоту текста
- **Решение:** Semantic сам делает черновой layout (`proposed_col_span` по минимальным правилам) и меряет текст под эту ширину через tool. Architect получает уже точные `height_cells` и финализирует композицию.

### Изменение col_span Architect-ом ломает измерения Semantic
- **Причина:** Architect может выбрать другую ширину (например 6+6 вместо 4+8) — тогда `height_cells` от Semantic неверен
- **Решение:** Validator при обнаружении изменённого `col_span` пере-меряет затронутые текстовые блоки через тот же tool. Это дешёво (один батч-вызов).

### Разные margins / неравномерное распределение
- **Причина:** контент прижат к верху, низ пустой
- **Решение:** layout_engine автоматически центрирует вертикально если сумма `height_cells` < 27. Architect не управляет margin вручную — это работа Python.

### LLM не калькулятор
- **Принцип:** все точные измерения (пиксели, клетки, размеры текста) делает Python
- **Реализация:** через прямые вызовы Python в постпроцессе **либо** через tool use из LLM
- Tool use не нарушает принцип — LLM не считает сама, она **просит Python посчитать**

### Состояние Фазы 4.9 (готово, но не запускается до 4.9.2)
- **Структурно** пайплайн готов: контракты, layout_engine, validator, retry-цикл orchestrator, multimodal Architect с PNG сетки — всё работает.
- **Не запускается** потому что Semantic Editor ещё выдаёт `line_budget`, а контракты требуют `proposed_col_span` + `height_cells`. Pydantic упадёт на валидации.
- **План:** Фаза 4.9.1 (tools + клиент) → Фаза 4.9.2 (Semantic с tool use). После этого можно запускать end-to-end и проверять реальные слайды.