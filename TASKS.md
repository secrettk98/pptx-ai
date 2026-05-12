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
- [x] models/contracts.py v4 — убрана SlideClassificationV2, добавлены BlockGeometry, SlideGeometry, slide_role в LayoutPlan
- [x] agents/architect.py — один агент вместо трёх (flash вместо pro)
- [x] prompts/architect.md — единый промпт (classify + layout в одном шаге)
- [x] core/prompt_assembler.py — assemble_rules(strategy) вместо assemble_prompt(classification)
- [x] Быстрые фиксы: config.py 404 модели, Senior карточки 6+6, subtitle rule, allow_rewrite
- [x] Чистка: удалены classifier.py, senior_designer.py, junior_designer.py, grid_calculator.py
- [x] Чистка: удалены prompts/classifier.md, senior_designer.md, junior_designer.md

---

## 📋 ФАЗА 4.6: LayoutEngine + SVG Renderer + Orchestrator v4
Цель: полный рабочий пайплайн без Junior Designer.

### LayoutEngine
- [ ] core/layout_engine.py — compute_geometry(layout_plan, strategy) → SlideGeometry
- [ ] Эвристика высот: heading=70, text по строкам, card=равная высота
- [ ] Вертикальное центрирование в рабочей зоне (header_type A/B)
- [ ] Расчёт x/y/w/h для каждого блока

### SVG Renderer
- [ ] core/svg_renderer.py — render_slide(slide_geometry) → SVG строка
- [ ] Шаблоны: heading, text, card, table, placeholder (chart/visual)
- [ ] Text wrapping (Python, не LLM)
- [ ] Style modes: soft (rx=12) / strict (rx=0)

### Orchestrator v4
- [ ] core/orchestrator.py — переписать: Parser → Strategy → Architect → LayoutEngine → SVG Renderer
- [ ] Кэш: strategy.json, layout_plan, svg
- [ ] CLI: --no-cache, --no-vision, --no-batch, --slides, --accent

### Тест
- [ ] Прогон на 1 слайде (--slides=0)
- [ ] Сравнение: качество vs старый пайплайн

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
- [ ] SVG word-wrap не всегда работает
- [ ] Постпроцессор скругляет ВСЕ Rectangle (нужно по style_mode)
- [ ] map_pipeline шаги 4-5 заглушки

---

## 📝 Решения принятые
- Architect = Classifier + Senior (1 шаг вместо 2, flash вместо pro)
- Junior УДАЛЁН — Python LayoutEngine + SVG Renderer
- LLM мыслит в grid-колонках, Python считает пиксели
- Strategy Director — 1 вызов flash на всю презу (~$0.002)
- Architect: поштучно с vision / батч до 10 без vision
- Дизайн-система: 12 колонок, 6 типов объектов
- Промпты модульные: core_rules + style + header + card + patterns
- system_instruction для всех агентов
- header_type на уровне презентации (из Strategy)
- Кэш: temp/cache/ (strategy, layout_plan, svg)
- Orchestrator CLI: --no-cache, --no-vision, --no-batch, --slides, --accent
- Тесты только на 1 слайде, потом расширяем

## ⚡ Экономия от v4
- Убран Junior (pro модель) → экономия ~70% токенов на слайд
- Classifier + Senior (2 вызова) → Architect (1 вызов flash) → экономия ~80%
- 5 слайдов: было 11 API вызовов → стало 6
- 100 слайдов: было 201 вызов → стало ~11 (батч)