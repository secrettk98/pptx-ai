# PPTX-AI — Project Context

## Продукт
B2B AI-сервис редизайна и генерации презентаций PowerPoint. PPTX + акцент → AI → нативный редактируемый PPTX.

## Принцип
LLM — мозг (стратегия, layout-план). Python — руки (парсинг, **flex-layout**, **точные метрики**, SVG-рендер, сборка). Только нативные элементы PowerPoint, никаких PNG/PDF.

## Архитектура v4 (МАЙ 2026, обновлено в Фазе 4.7)

1. **Parser [Python]** → ParsedPresentation
2. **Strategy Director [AI flash]** → PresentationStrategy (1 вызов на презу)
3. **Architect [AI flash]** → LayoutPlan
4. **LayoutEngine v5 [Python + stretchable + Pillow]** → SlideGeometry с RenderedText ✅
5. **SVG Renderer v5 [Python]** → SVG (тупой, рисует по готовым координатам) 🔄 в работе
6. **Reverse block** → Map / Chart / Scheme / Image — TODO
7. **Валидатор [Python]** — TODO
8. **Inspector [AI]** — TODO
9. SVG Engine → PPTX → Постобработка → Клиент

## Что работает
- ✅ Parser (parse_pptx_rich)
- ✅ Strategy Director, Architect
- ✅ Контракты v4 + RenderedText
- ✅ **LayoutEngine v5** — flex/grid через stretchable, точные метрики через Pillow + Inter
- ⚠️ SVG Renderer v4 — старый, надо переписать под RenderedText (Шаг 4)
- ✅ Orchestrator v4
- ✅ SVG Engine, Постпроцессоры
- ✅ google.genai SDK + Vertex AI (powermagic, us-central1)

## Что нужно сделать (приоритет сверху)
- 🔄 **Шаг 4: переписать core/svg_renderer.py v5** — тупой рендерер по RenderedText
- ❌ Добавить в layout_engine координаты обёрток (cell_x/y/w/h, card_x/y/w/h) в RenderedText.extra
- ❌ Прогон на реальных презентациях, итерация качества
- ❌ Валидатор, Inspector
- ❌ Подключить reverse-модули

---

## 🆕 Технологии Фазы 4.7

### stretchable (flex/grid layout)
- Python bindings для **Taffy** (Rust, fork Stretch). Multi-platform, MIT.
- `pip install stretchable`
- **Особенности API:**
  - `Style` — frozen, все параметры в `Node(...)` сразу
  - Enum-ы: `FlexDirection.COLUMN/ROW`, `AlignItems.STRETCH`, `JustifyContent.CENTER/FLEX_START`
  - `flex_basis=0` + size в `PCT` — настоящая grid-сетка без intrinsic-влияния
  - `measure_func(node, known_dimensions, available_space) → SizePoints`
  - `known.width.value` — float, может быть NaN
  - `available.width.scale` — `POINTS` / `MIN_CONTENT` / `MAX_CONTENT`
  - `node.get_box(Edge.BORDER)` — координаты **относительно родителя** (не абсолютные!)
  - Абсолютные координаты — суммой по дереву (`_abs_box` в layout_engine.py)
- **Запуск:** `python -m core.layout_engine` (не `python core/layout_engine.py`)

### Pillow + Inter (text metrics)
- `pip install pillow`
- Шрифт: `assets/fonts/Inter-Regular.ttf` + `Inter-Bold.ttf` (копии Inter-4.1 InterVariable.ttf)
- Источник: https://github.com/rsms/inter/releases/tag/v4.1
- `core/text_metrics.py`:
  - `measure(text, size_pt, bold)` → ширина в px
  - `wrap(text, max_w, size_pt, bold)` → list[str]
  - `fit_height(lines, size_pt)` → высота в px
  - `measure_block(text, max_w, size_pt, bold)` → (w, h, lines)
  - `truncate(text, max_w, size_pt)` → str с …
  - lru_cache на загрузку шрифтов

---

## Окружение
- Windows 11, PowerShell, VS Code, Python 3.14.4
- SDK: google-genai, Vertex AI ($300 credits)
- Модели: gemini-2.5-flash, gemini-2.5-pro
- LibreOffice 26.2, Poppler 25.12, gcloud CLI
- **Новое:** stretchable, Pillow 12.2, Inter variable TTF

## Модели (config.py)
- MODEL_CLASSIFIER: gemini-2.5-flash (Architect + Strategy Director)
- MODEL_BRAIN: gemini-2.5-pro (зарезерв.)
- MODEL_DESIGNER: gemini-2.5-pro (зарезерв.)
- MODEL_VISION: gemini-2.5-flash (зарезерв.)
- MODEL_INSPECTOR: gemini-2.5-flash
- MODEL_CHEAP: gemini-2.5-flash-lite

## Команда
- **Tech Lead (Claude Opus 4.7)** — логика, архитектура, код
- **Operator (Алишер)** — открывает файлы, копирует код, нажимает кнопки

## Формат ответа Техлида
1. 📁 Файл: точное имя
2. 🖱️ Действие для Оператора
3. 💾 Код **точечно** (не файл целиком, если правка): "найди строку X, замени на Y"
4. 🧠 Примечание (опционально)

## Правила
- Экономим токены и деньги
- Тесты только на 1 слайде (--slides=0)
- Перед правкой большого файла — Techlead обязан прочитать его актуальную версию
- PowerShell: команды по одной
- **Точечные правки** вместо полного файла, кроме случаев нового файла или полной переписи
- GitHub: https://github.com/secrettk98/pptx-ai

## Ключевые файлы (v5)
- **core/orchestrator.py** — главный пайплайн v4
- **core/layout_engine.py** — v5 (stretchable + Pillow), `compute_geometry(plan, strategy) → SlideGeometry`
- **core/layout_engine_v4.py** — резерв старой версии
- **core/svg_renderer.py** — v4 (нужно переписать в Шаге 4)
- **core/svg_renderer_v4.py** — резерв старой версии
- **core/text_metrics.py** — 🆕 точные метрики Pillow + Inter
- **core/llm_client.py** — вызовы API
- **core/prompt_assembler.py** — assemble_rules(strategy)
- **core/llm_normalize.py** — нормализация
- **agents/strategy_director.py** — единая стратегия
- **agents/architect.py** — classify + layout
- **models/contracts.py** — Pydantic модели v4 + 🆕 RenderedText, rendered_texts в BlockGeometry
- **parsers/pptx_parser.py** — parse_pptx_rich
- **parsers/slide_renderer.py** — PPTX → JPG
- **config/** — правила .md
- **prompts/** — промпты .md
- **reverse/** — модули реверса (не подкл.)
- **assets/fonts/Inter-Regular.ttf, Inter-Bold.ttf** — 🆕 шрифт
- **tools/check_stretchable.py, check_measure_func.py** — 🆕 диагностика

## Активные контракты (models/contracts.py)
GroupPosition, ShapeStyle, ParsedShape, ParsedSlide, ParsedPresentation,
PresentationStrategy,
ColumnInstruction, RowInstruction, FooterInstruction, LayoutPlan,
**RenderedText** 🆕, BlockGeometry (+rendered_texts), SlideGeometry,
DesignedSlide

---

## 🚨 ВАЖНО для нового чата

**Где мы остановились:** LayoutEngine v5 готов и протестирован (3 smoke-теста зелёные). На очереди — **Шаг 4: переписать `core/svg_renderer.py` под новый контракт `RenderedText`**.

**Прежде чем писать SVG рендерер**, нужно сделать **микро-доработку LayoutEngine** — добавить в `RenderedText.extra` координаты обёрток:
- Для табличных текстов (`role="cell_header"/"cell_body"`): `extra["cell_x", "cell_y", "cell_w", "cell_h"]`
- Для карточечных текстов (`role="card_*"`): `extra["card_x", "card_y", "card_w", "card_h"]`

Это нужно SVG-рендереру чтобы рисовать фоны карточек и линии таблицы по точным координатам ячеек, а не текстов.

**После этого** — собственно `svg_renderer.py v5`:
- Тупой рендерер по готовым координатам
- Никаких wrap/truncate/измерений
- Логика рисования: фон блока → линии → текст
- Структура: `_draw_block_bg`, `_draw_block_texts`, `_draw_heading_line`, `_draw_card_icon`, `_draw_table_grid`, `_draw_footer`

**Решения принятые перед Шагом 4:**
- Вариант 1 для обёрток (через `extra` в RenderedText, не новый контракт)
- SVG-рендерер не зависит от layout_engine — только от моделей