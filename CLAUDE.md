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
- **Layout:** ✅ чистый Python (детерминированная арифметика, без stretchable) — переписан в Фазе 4.10
- **LLM:** Gemini 2.5 Pro (семантика, layout) / Gemini 2.5 Flash (классификация, быстрые задачи)
- **Function calling:** Gemini native tool use для точных измерений текста/таблиц из LLM

---

## Правила кода (ЗАПРЕЩЕНО НАРУШАТЬ)
1. **Типизация:** type hints на всех функциях (параметры + return).
2. **Логирование:** только `logging.getLogger(__name__)`. `print()` запрещён.
3. **Ошибки:** строгие `try/except` с внятными сообщениями. Пустой `except` запрещён.
4. **Модели:** только Pydantic `BaseModel`. `dataclass` запрещён. Исключение: `@dataclass` для внутренних контейнеров layout_engine.
5. **Конфиг:** API ключи только из `.env` через `dotenv`. Хардкод запрещён.
6. **Пути:** только `pathlib.Path`. Строки для путей запрещены.
7. **Константы:** `UPPER_CASE` в начале файла. Глобальные переменные запрещены.
8. **Структура:** один файл = один модуль. Функции до 30 строк. Комментарии только там где логика неочевидна. `import *` запрещён.
9. **Hard Bans:** `MORPH_CLOSE`, `vtracer`, `pypotrace`, `EasyOCR`, `keras-ocr`, `&&` в PowerShell.
10. **Масштабируемость:** Код пишется универсальным — не под конкретный пример или кейс. Никаких magic numbers (все цифры → константы в `config.py`). Если параметр может измениться — он должен приходить снаружи (аргумент, конфиг, контракт). Думай: "что если слайдов будет 100, колонок 16, или размер изменился на 1920×1080?"
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
│   ├── layout_engine.py     # ✅ v5.1 — чистый Python без stretchable
│   ├── svg_renderer.py
│   ├── llm/
│   │   ├── client.py        # есть call_llm + call_llm_with_tools
│   │   ├── normalize.py
│   │   ├── tools.py         # реестр tools для function calling
│   │   └── ollama.py
│   └── utils/
│       ├── text_metrics.py  # measure/wrap + measure_text_in_cells/measure_table_in_cells
│       ├── grid_visualizer.py
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
│   └── validator.py
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

LLM = мозг. Python = руки. Только Agentic Workflow. LLM умеет **звать Python через tools** — это не нарушает принцип, а усиливает его: LLM думает, Python считает.

### Слой 0 — Semantic Editor (`agents/semantic_editor.py`)
- Модель: **Gemini 2.5 Pro** + Chain of Thought `<thinking>` + **Tool Use**
- Вход: `ParsedSlide` + скриншот слайда + design_context
- Что делает:
  1. Убирает "воду", выявляет Intent, группирует смыслы
  2. **Накидывает черновой layout** — `proposed_col_span` на каждый блок по минимальным правилам
  3. **Меряет текст и таблицы через tool** `measure_texts_batch` — получает точный `height_cells`
  4. Для `chart` / `visual` / `image` / `card` высоту считает сам (chart 8-14 клеток, visual 8-14, card по формуле `len(cards)*4+1`)
  5. LLM сама передаёт `style: {size_pt, bold, line_factor}` в tool — без хардкода в Python
- Выход: `SemanticSlide` (список `SemanticBlock` с `proposed_col_span` и точным `height_cells`)
- **Строго сохраняет все визуальные элементы** (chart, visual, table) из оригинала
- **Никогда не переводит контент** — сохраняет язык оригинала
- **Минимизирует tool calls** — один батч-вызов на все текстовые блоки

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
- Финализирует композицию: `row_start_cell`, `col_start`, `col_span`, выравнивание
- Может **перераспределить колонки** (например 6+6 вместо 4+8) — но тогда нужно пере-измерить текст
- Выход: `LayoutPlanV5` (`GridRow` + `GridBlock` с `row_start_cell`, `col_start`, `col_span`, `height_cells`)
- **НЕ получает и НЕ возвращает content** — контент подставляет orchestrator (`_enrich_layout()`)

### Слой 1.5 — Enrich (`core/orchestrator.py` → `_enrich_layout()`)
- Чистый Python, без LLM
- Матчит `GridBlock.block_id` → `SemanticBlock`
- Копирует `content`, `semantic_type`, `visual_subtype` в GridBlock

### Слой 2 — Визуальные модули (`agents/`) — бэклог
- Image Generator, Map Redesigner, Flowchart, Chart, Pattern, Custom Infographic
- Хук для API иконок по `icon_concept`

### Слой 2.5 — Python Validator (`postprocess/validator.py`)
- Прогоняет LayoutPlanV5 на уровне **клеток** (не пикселей!)
- Проверки: negative coords, horizontal overflow, vertical overflow, overlap (матрица 12×27)
- Penalty по весам из config
- Формирует текстовый feedback → отправляет Spatial Architect-у
- Максимум `MAX_VALIDATOR_RETRIES` попыток (default 2), потом берёт **лучший** по минимальному penalty
- Дампит все попытки в `output/debug/slide_{N}/attempt_{M}.json` + финальный `chosen.json`
- `ValidationResult.changed_col_spans` — словарь блоков, у которых Architect изменил ширину относительно `proposed_col_span`
- **TODO:** orchestrator пока только логирует `changed_col_spans` warning'ом — пере-измерение через tool не подключено

### Слой 3 — AI Inspector (`agents/inspector.py`) — бэклог
- Финальная проверка: семантика сохранена + дизайн соответствует системе

---

## Tool Use — реестр tools (`core/llm/tools.py`)

### Доступные tools для Semantic Editor

| Tool | Назначение | Аргументы | Возврат |
|---|---|---|---|
| `measure_texts_batch` | Точная высота текста и таблиц в клетках | `items: list[{block_id, kind, text/table_data, width_cols, style}]` | `{heights: dict[block_id, height_cells]}` |

`check_total_budget` **удалён из реестра** — Semantic не знает раскладку по рядам, проверка бюджета на этом этапе бессмысленна. Реальную проверку делает Validator уже после Spatial Architect.

### Принципы tool use
1. **Минимум round-trips:** один батч-вызов на все блоки, не по одному
2. **Только для текста и таблиц:** chart/visual/image/card LLM считает сама по правилам
3. **Лимит вызовов:** `MAX_TOOL_CALLS_PER_SLIDE = 5` в config
4. **Логирование:** каждый tool call логируется

### Реализация в `core/llm/client.py`
- Старый `call_llm()` не тронут — работает как раньше
- Новый `call_llm_with_tools()` — function calling loop с лимитом и логированием
- Поддерживает multimodal (image_path), system_instruction, лимит итераций

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
- `priority` (1-10, важность для компрессии при overflow)
- `proposed_col_span: int` — черновая ширина от Semantic (1-12)
- `height_cells: int` — **точная высота в клетках**, измерена через tool или посчитана LLM

### GridBlock — разделение ответственности
- **LLM (Architect) заполняет:** `block_id`, `row_start_cell`, `col_start`, `col_span`, `height_cells`, `render`
- **Python (enrich) заполняет:** `semantic_type`, `content`, `visual_subtype`

### GridRow — ключевые поля
- `row_id`, `row_start_cell: int`, `height_cells: int`, `blocks: list[GridBlock]`

---

## Design System

| Параметр | Значение |
|---|---|
| Слайд | 1280 × 720 px |
| Отступы слайда | 42px гор., 22px верт. |
| layout_canvas (рабочая область) | 1196 × 676 px |
| **Сетка** | **12 колонок × 27 строк** |
| Размер клетки | ~99.67 × 25.04 px |
| Gap между рядами | 1 клетка (~25 px), фиксированный |
| Внутренний padding карточки/блока | 12 px (`CARD_PADDING_PX`) |
| Мин. ширина колонки таблицы | 40 px (`MIN_COL_WIDTH_PX`) |
| Отступ текста буллета от точки | 18 px (`BULLET_TEXT_OFFSET_PX`) |
| Шрифт | Google Sans / Inter (fallback) |
| Акцент по умолчанию | #0066CC |

### Стандартные размеры шрифтов (рекомендации LLM, не хардкод)

| Элемент | size_pt | bold |
|---|---|---|
| heading title | 24 | true |
| heading subtitle | 14 | false |
| text title (подзаголовок блока) | 14 | true |
| text body / bullets | 12 | false |
| text caption (серый вспомогательный) | 10 | false |
| table headers | 12 | true |
| table cells | 10 | false |

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
   - 3e. **Validator** → OK или feedback → retry 3c-3d (макс. `MAX_VALIDATOR_RETRIES`), либо лучший по penalty
   - 3f. Layout Engine → SlideGeometry (конвертация клетки → пиксели, чистая арифметика)
   - 3g. SVG Renderer → DesignedSlide (SVG код)

---

## Таск-трекер

### ✅ Завершено
- Фазы 0-4.4: парсер, контракты, Strategy Director, Vertex AI
- Фаза 4.7: LayoutEngine v5 (stretchable + Pillow, точные метрики текста)
- Фаза 4.7.1: SVG Renderer v5
- Фаза 4.8: контракты v5, prompt_assembler, orchestrator v5 с enrich
- Фаза 4.8.1: semantic_editor.py, spatial_architect.py — агенты написаны
- Фаза 4.8.2: промпты semantic_editor.md и spatial_architect.md обновлены
- **Фаза 4.9: Сетка клеток 12×27 + Validator** ✅
  - `core/config.py` — добавлены `GRID_COLS=12`, `GRID_ROWS=27`, `CELL_WIDTH≈99.67`, `CELL_HEIGHT≈25.04`, `ROW_GAP_CELLS=1`, `MAX_VALIDATOR_RETRIES=2`, `MAX_TOOL_CALLS_PER_SLIDE=5`, `CARD_PADDING_PX=12`, веса penalty, `DEBUG_DIR`
  - `models/contracts.py` — переход на `height_cells` / `proposed_col_span` / `row_start_cell`
  - `core/layout_engine.py` — переписан под клеточную сетку с независимыми stretchable-деревьями на блок
  - `core/utils/grid_visualizer.py` — рендер PNG сетки 12×27
  - `postprocess/validator.py` — валидатор + дамп попыток
  - `agents/spatial_architect.py` + промпт — работа в клетках, multimodal с PNG сетки
  - `core/orchestrator.py` — цикл `_design_with_retry()` Architect→Enrich→Validate

- **Фаза 4.9.1: Tool use инфраструктура** ✅
  - `core/llm/tools.py` — реестр с tool `measure_texts_batch`. `check_total_budget` решили не делать (избыточный round-trip)
  - `core/llm/client.py` — добавлен `call_llm_with_tools()` с function calling loop (лимит `MAX_TOOL_CALLS_PER_SLIDE`)
  - `core/utils/text_metrics.py` — добавлены `measure_text_in_cells()` и `measure_table_in_cells()`
  - LLM сама передаёт `style: {size_pt, bold, line_factor}` в tool — без хардкода в Python

- **Фаза 4.9.2: Semantic Editor с tool use** ✅
  - `agents/semantic_editor.py` — использует `call_llm_with_tools` с `TOOL_DECLARATIONS`/`TOOL_HANDLERS`
  - `prompts/semantic_editor.md` — переписан под сетку 12×27, минимальные правила col_span, инструкции по tool use, дефолты шрифтов, правила высоты для card/chart/visual/heading
  - Точечный фикс в `orchestrator.py`: `semantic.total_lines` → `semantic.total_height_cells`

- **Фаза 4.10: Layout Engine v5.1 — чистый Python (Вариант A)** ✅
  - `core/config.py` — добавлены `MIN_COL_WIDTH_PX=40`, `BULLET_TEXT_OFFSET_PX=18`
  - `core/layout_engine.py` — **полностью переписан** без stretchable. Детерминированная арифметика: курсор по Y внутри блока, wrap текста через `text_metrics.wrap()` по фиксированной `inner_w = col_span × CELL_WIDTH - 2*CARD_PADDING_PX`. Реализованы `_layout_heading`, `_layout_text`, `_layout_card`, `_layout_table`, `_layout_placeholder`. Алгоритм ширин колонок таблицы — Вариант A (пропорционально natural width с границей по `MIN_COL_WIDTH_PX` и longest word width)
  - `core/svg_renderer.py` — точечно: `bullet_offset` теперь импортируется из `config.BULLET_TEXT_OFFSET_PX`
  - **Результат:** таблица рендерит все колонки, bullets делают wrap, нет stretchable, нет повторного wrap

### 🔄 В работе

**Фаза 4.10.1 — Диагностика расхождения план ↔ SVG (КРИТИЧНО)**

После рефакторинга layout_engine обнаружено расхождение: координаты в финальном SVG не соответствуют `col_span` из `chosen.json`.

**Симптомы:**
- План в `chosen.json`: text-блок `col_start=0, col_span=7`, donut `col_start=7, col_span=5`
- Реальный SVG: text-блок `x=42, w=797.3` (= col_span 8), donut `x=839.3, w=398.7` (= col_span 4)
- Block_id в SVG-комментариях не соответствуют block_id из плана (`sb3` в комментарии = text, в плане = chart)
- Bullets рендерятся в ширину 8 колонок, donut в 4 → визуально text-блок упирается в donut без зазора

**Гипотезы:**
1. После Validator план модифицируется перед передачей в `compute_geometry` (нужно прочитать orchestrator и validator целиком)
2. В `output/` остаётся старый SVG от предыдущего прогона, debug-дамп от нового — проверить времена создания файлов
3. `_enrich_layout` сам по себе чист (прочитан), col_span не трогает — значит изменение происходит между enrich и layout_engine

**Что делать в новом чате:**

1. **Найти физическое расположение `output/debug/`** (PowerShell не нашёл по ожидаемому пути):
   ```powershell
   Get-ChildItem -Path . -Recurse -Filter "chosen.json" -ErrorAction SilentlyContinue | Select FullName, LastWriteTime
   Get-ChildItem -Path . -Recurse -Filter "*.svg" -ErrorAction SilentlyContinue | Select FullName, LastWriteTime
   ```

2. **Чистый прогон от нуля:** удалить старые SVG + debug-дампы, перезапустить, сразу сравнить времена создания SVG и `chosen.json`:
   ```powershell
   Remove-Item output\*.svg -Force -ErrorAction SilentlyContinue
   Remove-Item output\debug\* -Recurse -Force -ErrorAction SilentlyContinue
   python -m core.orchestrator projects\test_map\test_maps.pptx --no-cache --slides=0
   ```

3. **Если расхождение подтверждается** — прочитать `core/orchestrator.py` целиком (цикл `_design_with_retry`, что именно передаётся в `compute_geometry` после Validator) и `postprocess/validator.py` (не модифицирует ли план in-place).

4. **После фикса расхождения** — приступить к overflow detection (поле `actual_content_height_px` в `BlockGeometry` + retry loop в orchestrator).

**Открытые косметические вопросы** (НЕ блокирующие, решено игнорировать):
- Заголовок в UPPERCASE приходит из Semantic Editor или Parser в content — это особенность исходных данных, не баг рендеринга.

### 📋 Бэклог

**Фаза 4.11 — Overflow detection через LLM retry**
- [ ] Расширить `BlockGeometry` полем `actual_content_height_px: float`
- [ ] Layout Engine считает фактическую высоту контента после wrap
- [ ] Orchestrator после `compute_geometry` проверяет каждый блок на overflow
- [ ] При overflow → собирает feedback → новый виток retry через Spatial Architect (отдельно от Validator retry)
- [ ] Подключить пере-измерение через tool при `changed_col_spans` (сейчас только warning)

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

### Layout Engine v5.1 — чистый Python
**Статус:** ✅ переписан в Фазе 4.10. Stretchable полностью удалён.

**Архитектура:**
- Размер блока приходит сверху: `col_span × CELL_WIDTH`, `height_cells × CELL_HEIGHT`
- Внутри блока — детерминированная арифметика: курсор по Y, элементы расставляются сверху вниз с фиксированными gap'ами
- Wrap текста один раз через `text_metrics.wrap()` по `inner_w = block_w - 2*CARD_PADDING_PX`
- Координаты в `RenderedText` синхронны с шириной wrap → svg_renderer рендерит ровно то, что было измерено
- Каждый `semantic_type` — отдельная функция-раскладчик (`_layout_heading`, `_layout_text`, `_layout_card`, `_layout_table`, `_layout_placeholder`)

**Алгоритм ширин колонок таблицы (Вариант A):**
1. `natural[j] = max(header_w, max_cell_w) + 2*PAD_TBL_X`
2. `min_w[j] = max(longest_word_w, MIN_COL_WIDTH_PX) + 2*PAD_TBL_X`
3. Если `sum(natural) <= inner_w` → раздать остаток пропорционально natural
4. Если `sum(natural) > inner_w` → сжать пропорционально, но не ниже `min_w[j]`
5. Если `sum(min) > inner_w` → physical overflow, warning, используются `min_w`

**Контракты не менялись:** `BlockGeometry`, `RenderedText`, `SlideGeometry` — те же.

### Расхождение план ↔ SVG (текущая блокирующая проблема)
**Симптом:** координаты блоков в финальном SVG не совпадают с `col_span` из `chosen.json`. Подробности см. в "Фаза 4.10.1 — Диагностика расхождения".

**Гипотеза рабочая:** либо план модифицируется где-то между Validator и `compute_geometry`, либо в `output/` остаётся старый SVG от предыдущего прогона. Диагностика — в новом чате.

### Overflow (контент не влезает в слайд)
- **Причина:** LLM плохо считает пиксели и не знала точную ширину блока на этапе семантики
- **Решение трёхуровневое:**
  1. **Semantic Editor** меряет текст через tool `measure_texts_batch` ещё до Architect → outputs точный `height_cells`
  2. **Сетка 12×27 клеток** вместо пикселей → LLM мыслит дискретно
  3. **Validator** ловит остаточные ошибки и даёт feedback Architect-у (макс 2 retry)
- **НЕ решение:** костыли в промптах типа "убери карточки если не влезает"
- **TODO Фаза 4.11:** добавить ещё один уровень — overflow detection внутри блока после рендера (Layout Engine считает actual height → orchestrator сравнивает с выделенной → retry LLM)

### "Курица и яйцо" между Semantic и Architect
- **Причина:** Semantic не знал ширину блока, Architect не знал реальную высоту текста
- **Решение:** Semantic сам делает черновой layout (`proposed_col_span`) и меряет текст под эту ширину через tool. Architect получает уже точные `height_cells` и финализирует композицию.

### Изменение col_span Architect-ом ломает измерения Semantic
- **Причина:** Architect может выбрать другую ширину (например 6+6 вместо 4+8) — тогда `height_cells` от Semantic неверен
- **Решение:** Validator при обнаружении изменённого `col_span` пере-меряет затронутые текстовые блоки через тот же tool
- **Статус:** Validator детектит изменения и заполняет `changed_col_spans`, но orchestrator пока только логирует warning. Подключение пере-измерения — TODO в Фазе 4.11

### Разные margins / неравномерное распределение
- **Причина:** контент прижат к верху, низ пустой
- **Решение:** layout_engine автоматически центрирует вертикально если сумма `height_cells` < 27 (`_compute_auto_shift_cells`). Architect не управляет margin вручную — это работа Python

### LLM не калькулятор
- **Принцип:** все точные измерения (пиксели, клетки, размеры текста) делает Python
- **Реализация:** через прямые вызовы Python в постпроцессе **либо** через tool use из LLM
- Tool use не нарушает принцип — LLM не считает сама, она **просит Python посчитать**

### Состояние end-to-end теста (Фаза 4.10 завершена)
- ✅ Strategy Director → корректно
- ✅ Semantic Editor с tool use → точные `height_cells`, tool вызывается батчем
- ✅ Spatial Architect с PNG сетки → корректный layout, `changed_col_spans={}`, валидный план
- ✅ Validator → подтверждает план, дампит в `output/debug/`
- ✅ Layout Engine v5.1 → таблица показывает все колонки, bullets делают wrap
- ⚠️ SVG Renderer → координаты не соответствуют плану из `chosen.json` (см. Фаза 4.10.1)

**Тестовый слайд** (`projects/test_map/test_maps.pptx`, слайд 0): heading + chart(7col) + table(5col) + text(7col) + chart-donut(5col). После Фазы 4.10 таблица и bullets рендерятся корректно по своему col_span, но финальные координаты блоков в SVG не сходятся с планом — нужна диагностика.