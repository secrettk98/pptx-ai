# PPTX-AI — Task Tracker

## ✅ Завершено

### Фазы 0-3 (база)
- Структура, контракты, парсер, конвертер, AI-агенты v1, SVG Engine
- Миграция на google.genai + Vertex AI
- Map Pipeline ~80% (classifier, splitter, background, objects, assembler)
- Обогащённый парсер parse_pptx_rich()
- Ollama client (core/ollama_client.py)

### Фаза 4.1-4.2: Архитектура v2 + Дизайн-система
- agents v2 (classifier, senior, junior) + system_instruction
- orchestrator v2 с кэшем, батчами, async
- llm_client (sync + async), prompt_assembler, llm_normalize
- contracts v2, промпты v2
- config/: core_rules, classifier, card, patterns, modules_map, handoff, headers/, styles/

### Фаза 4.3: Чистка кода v1
- Удалены агенты v1: brain.py, designer.py, vision_classifier.py
- Удалены промпты v1, отчищен contracts.py

### Фаза 4.4: Strategy Director
- agents/strategy_director.py + prompts/strategy_director.md
- PresentationStrategy (header_type, style_mode, accent_color, presentation_mode, allow_rewrite)
- Мульти-изображения в call_llm, CLI --accent

### Фаза 4.5: Архитектура v4 — Architect (МАЙ 2026)
- [x] Решение: объединить Classifier + Senior + Junior → Architect + LayoutEngine + SVG Renderer
- [x] models/contracts.py v4 — BlockGeometry, SlideGeometry, slide_role в LayoutPlan
- [x] agents/architect.py — один агент вместо трёх (flash вместо pro)
- [x] prompts/architect.md — единый промпт (classify + layout в одном шаге)
- [x] core/prompt_assembler.py — assemble_rules(strategy)
- [x] Чистка: удалены classifier.py, senior_designer.py, junior_designer.py, grid_calculator.py + промпты

### Фаза 4.6: LayoutEngine + SVG Renderer + Orchestrator v4 (МАЙ 2026)
- [x] core/layout_engine.py v4 — compute_geometry, эвристики высот (на самопальных _char_em)
- [x] core/svg_renderer.py v4 — render_slide, рендереры heading/text/card/table/placeholder
- [x] core/orchestrator.py v4 — полный пайплайн
- [x] Кэш: strategy.json, layout_plan, geometry, svg
- [x] CLI: --no-cache, --no-vision, --no-batch, --slides, --accent

### Фаза 4.7 (МАЙ 2026): Универсальный движок на stretchable + Pillow ✅
**Решение:** заменили самописный LayoutEngine на промышленный flex/grid + точные метрики Pillow.

- [x] **stretchable** (Python bindings Taffy, Rust) — flex/grid/block layout движок
- [x] **Pillow + Inter (variable TTF)** — точное измерение текста (1/64 px)
- [x] **assets/fonts/Inter-Regular.ttf, Inter-Bold.ttf** — копии InterVariable.ttf
- [x] **core/text_metrics.py** — measure / wrap / fit_height / truncate / measure_block, lru_cache
- [x] **models/contracts.py** — добавлен `RenderedText` (role, lines, x/y/w/h, size_pt, bold, extra)
- [x] **models/contracts.py** — `BlockGeometry.rendered_texts: list[RenderedText]`
- [x] **core/layout_engine.py v5** — переписан на stretchable + точные метрики:
  - SlideRoot (flex column, padding=margins)
  - HeaderRow [optional, type A: 70px]
  - ContentRoot (flex column, flex_grow=1, justify=center для type B/C)
  - Row (flex row, gap=26, align_items=STRETCH)
  - Колонки = "слоты" с **точной шириной в процентах** (избегаем intrinsic-расчёта)
  - Текстовые блоки = листы с `measure_func` (Pillow считает реальную высоту)
  - Карточки = вложенный flex column с padding=18, gap=6
  - Таблицы = flex column из row-ячеек, веса колонок min=60 max=200
- [x] **core/layout_engine_v4.py, core/svg_renderer_v4.py** — резервные копии старой версии

**Smoke-тесты прошли:**
- Тест 1 (heading + text/bullets 6+6): w=584 каждый, центрирование Y ✅
- Тест 2 (3 карточки grid_span=4): w=380.7 одинаковые, высоты выравниваются (align_items=STRETCH) ✅
- Тест 3 (таблица 4 колонки): пропорциональные ширины ✅

---

## 🔄 ТЕКУЩАЯ РАБОТА: Шаг 4 — переписать `core/svg_renderer.py` v5

**Концепция:** SVG-рендерер становится **тупым**. Получает готовые координаты `RenderedText` от LayoutEngine и просто рисует. Никаких wrap/truncate/измерений.

### План Шага 4
1. **Фоны и обводки** — `_draw_block_bg(block)`: card → C_CARD fill, placeholder → пунктир, table → рамка
2. **Текст** — проход по `block.rendered_texts`: рисуем строки с size_pt/bold/координатами как есть
3. **Спец-элементы карточек** — `RenderedText` с `role="card_icon"` → кружок акцентом + буква из `extra["icon_char"]`
4. **Линия акцента под heading** — по координатам блока
5. **Footer** — копируем из v4 без изменений
6. **Таблица** — обводки/зебра по `extra: {row, col}` из rendered_texts

### Открытый вопрос перед кодом
**В Шаге 3 РЕШИЛИ:** идём по **Варианту 1** — добавляем в `RenderedText.extra` координаты обёрток:
- Для табличных текстов: `extra["cell_x/y/w/h"]` — координаты ячейки
- Для карточечных текстов: `extra["card_x/y/w/h"]` — координаты карточки

Это нужно SVG-рендереру для отрисовки фонов карточек и линий таблицы. Сейчас в layout_engine этого ещё НЕТ — нужно добавить точечно.

### Что осталось НЕ покрытым LayoutEngine v5 (хвосты)
- [ ] composition_schema B, C, D (сейчас всё идёт как вертикальный стек рядов — но flex это поддерживает, добавим за 20 строк)
- [ ] Header Type A — фиксированный хедер из шаблона (узел резервирует место, рендер в SVG)
- [ ] Иконки в карточках — пока заглушка через символ. Реальные SVG-иконки = отдельная задача

---

## 📋 ФАЗА 4.8: Тестирование на реальных презентациях
- [ ] Прогон на 1 слайде (--slides=0) с реальной презентацией
- [ ] Прогон на 3-5 слайдах, сравнение качества
- [ ] Визуальная проверка SVG в браузере
- [ ] Сквозной тест: PPTX → SVG → PPTX через SVG Engine

---

## 📋 ФАЗА 5: Валидатор + Inspector
- [ ] postprocess/validator.py — XML валидность, bounds, overlap, text overflow
- [ ] agents/inspector.py — AI визуальная проверка → цикл (макс 2 итерации)
- [ ] prompts/inspector.md

---

## 📋 ФАЗА 6: Реверс-модули
- [ ] Подключить map_pipeline к оркестратору
- [ ] reverse/chart_reverse.py (bar, pie, line)
- [ ] reverse/flowchart_reverse.py (Graphviz)
- [ ] reverse/image_generator.py

---

## 📋 ФАЗА 7: Оптимизация и тесты
- [ ] Кэш strategy между запусками одной презы
- [ ] Сжимать картинки для Strategy до 512×288 px
- [ ] Прогон SmartGas, Welcome, AI UDP
- [ ] pytest, метрики качества
- [ ] Цель: 80% успешных слайдов

---

## 🐛 Баги
- [x] ~~SVG word-wrap не всегда точный~~ → решено Pillow + Inter
- [x] ~~Постпроцессор скругляет ВСЕ Rectangle~~ → нужно проверить заново после нового рендера
- [ ] map_pipeline шаги 4-5 заглушки
- [ ] Иконки в карточках — заглушки (буква в кружке)

---

## 📝 Решения принятые (новые в Фазе 4.7)
- **stretchable** (Taffy bindings) — промышленный flex/grid движок вместо самописного
- **Pillow + Inter variable TTF** — точные метрики текста (1/64 px) вместо эвристики `_char_em`
- **Ширина колонок через PCT, не flex_grow** — иначе intrinsic-размер контента ломает grid
- **flex_basis=0 + размер в %** — настоящая 12-колоночная сетка
- **RenderedText в BlockGeometry** — layout мерит ОДИН раз, SVG только рисует
- **measure_func сигнатура:** `(node, known_dimensions, available_space) → SizePoints`
  - `known.width.value` может быть NaN; `available.width.scale` = POINTS/MIN_CONTENT/MAX_CONTENT
- **Style — frozen** — все параметры передаём в Node(...) сразу, не меняем после
- **Запуск файлов внутри пакетов:** `python -m core.layout_engine` (не `python core/layout_engine.py`)

---

## 📝 Решения принятые (старые)
- Architect = Classifier + Senior (1 шаг вместо 2, flash вместо pro)
- Junior УДАЛЁН — Python LayoutEngine + SVG Renderer
- LLM мыслит в grid-колонках, Python считает пиксели
- Strategy Director — 1 вызов flash на всю презу (~$0.002)
- Architect: поштучно с vision / батч до 10 без vision
- Дизайн-система: 12 колонок, 6 типов объектов
- Промпты модульные: core_rules + style + header + card + patterns
- system_instruction для всех агентов
- header_type на уровне презентации (из Strategy)
- Кэш: temp/cache/ (strategy, layout_plan, geometry, svg)
- Orchestrator CLI: --no-cache, --no-vision, --no-batch, --slides, --accent
- Тесты только на 1 слайде, потом расширяем
- SVG Renderer: чистый Python, без LLM-вызовов

## ⚡ Экономия от v4
- Убран Junior (pro модель) → экономия ~70% токенов на слайд
- Classifier + Senior (2 вызова) → Architect (1 вызов flash) → экономия ~80%
- LayoutEngine + SVG Renderer = Python (0 токенов, 0 стоимости)
- 5 слайдов: было 11 API вызовов → стало 6
- 100 слайдов: было 201 вызов → стало ~11 (батч)