# PPTX-AI — Task Tracker

## ✅ Завершено

### Фазы 0-3 (база)
- Структура, контракты, парсер, конвертер, AI-агенты v1, SVG Engine
- Миграция на google.genai + Vertex AI
- Map Pipeline ~80% (classifier, splitter, background, objects, assembler)
- Обогащённый парсер parse_pptx_rich()
- Ollama client (core/ollama_client.py)

### Фаза 4.1: Архитектура v2
- [x] agents/classifier.py — SlideClassificationV2, батч до 20, system_instruction
- [x] agents/senior_designer.py — LayoutPlan, батч до 10, system_instruction
- [x] agents/junior_designer.py — SVG по LayoutPlan, async до 5 параллельно
- [x] core/orchestrator.py — полный пайплайн с кэшем, батчами, async
- [x] core/llm_client.py — system_instruction + call_llm_async + semaphore
- [x] core/prompt_assembler.py — модульная сборка промптов
- [x] core/llm_normalize.py — нормализация ответов AI
- [x] core/grid_calculator.py — создан, НЕ подключён (отложен для LayoutEngine)
- [x] models/contracts.py — все контракты v2
- [x] prompts/senior_designer.md — промпт Senior
- [x] prompts/junior_designer.md — промпт Junior v2

### Фаза 4.2: Дизайн-система (конфиги)
- [x] config/core_rules.md — 12-колоночная сетка, 6 объектов
- [x] config/classifier.md — схема классификации
- [x] config/card.md — правила карточек
- [x] config/patterns.md — визуальные паттерны
- [x] config/modules_map.md — карта загрузки модулей
- [x] config/handoff.md — передача данных между агентами
- [x] config/headers/ — type_a, type_b, type_c
- [x] config/styles/ — strict.md, soft.md

### Фаза 4.3: Чистка кода (МАЙ 2026)
- [x] Удалены агенты v1: agents/brain.py, agents/designer.py, agents/vision_classifier.py
- [x] Удалены промпты v1: prompts/brain_level1.md, brain_level2.md, designer.md, vision_classifier.md
- [x] Отчищен models/contracts.py — удалены SlideInfo, PresentationStructure, SlideClassification, PresentationStrategy (v1), SlideBrief, ElementInfo, SlideGroup, ColorPalette, SlideClassificationFinal, BlockInstruction, DesignInstruction
- [x] Удалена устаревшая parse_pptx() из parsers/pptx_parser.py
- [x] Удалён дублирующий импорт calc_layout_geometry из agents/junior_designer.py
- [x] Удалён неиспользуемый импорт design_slide_junior из core/orchestrator.py
- [x] DesignedSlide.generation_time_ms — добавлен default=0

### Фаза 4.4: Strategy Director (МАЙ 2026)
- [x] models/contracts.py — добавлен PresentationStrategy (header_type, style_mode, accent_color, presentation_mode, allow_rewrite)
- [x] prompts/strategy_director.md — промпт с критериями выбора всех 5 полей
- [x] agents/strategy_director.py — агент build_strategy(images, parsed)
- [x] core/llm_client.py — call_llm теперь принимает image_path: str | list (мульти-изображения)
- [x] core/orchestrator.py — Strategy встроен как Шаг 3, кэшируется отдельно (strategy.json)
- [x] header_type: "fixed" → "A", "floating" → "B" (маппинг в orchestrator)
- [x] CLI: --accent=#XXXXXX перебивает strategy.accent_color

---

## 🔧 Нужно пофиксить (ПРИОРИТЕТ 1)

### Качество SVG
- [ ] Junior не центрирует контент вертикально — огромные пустоты внизу
- [ ] Senior кладёт несколько карточек в 1 колонку grid_span=12 вместо 6+6
- [ ] Senior создаёт отдельный text-ряд для короткого подзаголовка (должен быть subtitle)
- [ ] Junior получает LayoutPlan дважды — плейсхолдер {layout_plan} в системном промпте остаётся как литеральная строка (баг в _build_system_prompt)
- [ ] Промпт Junior перегружен (~5000 символов) — разбить на модули как у Senior через assembler

### Семантика
- [ ] Senior НЕ использует strategy.allow_rewrite — должен перефразировать тексты если true
- [ ] Strategy.accent_color часто = дефолтный #0066CC, плохо извлекает реальный цвет
- [ ] Classifier не оценивает существующие visuals (нет поля visual_assessment: keep/regenerate/remove)
- [ ] Classifier не возвращает семантические groups[] (Senior получает плоский objects[])

### Конфиг
- [ ] config.py: MODEL_INSPECTOR указывает на gemini-3.1-flash-lite-preview (404)
- [ ] config.py: MODEL_CHEAP указывает на gemini-3.1-flash-lite-preview (404)

---

## 📋 ФАЗА 4.5: LayoutEngine (Python геометрия)
Цель: убрать вычисление координат из LLM в Python. Решает проблему #1 (вертикальные пустоты).

- [ ] core/layout_engine.py — функция compute_geometry(layout_plan, strategy) → LayoutGeometry
- [ ] Эвристика высот блоков по содержимому (heading=70, text по строкам, card одинаковая высота)
- [ ] Вертикальное центрирование композиции в рабочей зоне (с учётом header_type A/B/C)
- [ ] Расчёт x/y/w для каждой колонки в каждом ряду
- [ ] Junior получает готовую LayoutGeometry, не считает координаты сам
- [ ] Сократить промпт Junior (убрать секцию POSITIONING RULES)
- [ ] Опционально: Pillow + TTF-шрифты для точных text metrics

---

## 📋 ФАЗА 4.6: Senior v2 — семантика
- [ ] prompts/senior_designer.md — добавить блок про allow_rewrite (можно перефразировать, сократить, объединить)
- [ ] agents/senior_designer.py — передавать strategy в design_slide_senior / design_batch_senior
- [ ] Запретить grid_span=12 для нескольких однотипных карточек (примеры в промпте: 2 карточки → 6+6, 3 → 4+4+4)
- [ ] Различать short text как subtitle vs отдельный text-ряд

---

## 📋 ФАЗА 4.7: Classifier v3
- [ ] models/contracts.py — добавить SlideGroup (group_id, role, elements, position) и visual_assessment
- [ ] SlideClassificationV2 → SlideClassificationV3 с полями groups[] и visual_assessment[]
- [ ] prompts/classifier.md — добавить инструкции по группировке и оценке visuals (keep/regenerate/remove)
- [ ] header_type и style_mode убрать из Classifier (приходят из Strategy)

---

## 📋 ФАЗА 4.8: Валидатор + Inspector
- [ ] postprocess/validator.py — XML валидность, bounds, overlap, text overflow
- [ ] agents/inspector.py — AI визуальная проверка → возврат к Senior (макс 2 итерации)
- [ ] prompts/inspector.md

---

## 📋 ФАЗА 5: Реверс-модули
- [ ] Подключить map_pipeline к оркестратору (когда Classifier научится оценивать карты)
- [ ] reverse/chart_reverse.py (bar, pie, line)
- [ ] reverse/flowchart_reverse.py (Graphviz)
- [ ] reverse/image_generator.py (Nano Banana 2)

---

## 📋 ФАЗА 6: Оптимизация и тесты
- [ ] Эксперимент: заменить MODEL_BRAIN (Senior) с pro на flash — потенциальная экономия 5-10x
- [ ] Кэш presentation_strategy между запусками одной презы
- [ ] Сжимать картинки для Strategy до 512×288 px (экономия токенов в 5 раз)
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
- Локальные модели (Ollama) ненадёжны — используем Gemini, но Ollama оставлен на будущее для простых задач
- Vision: простая роль, группировку делает Classifier
- Фильтрация мелких шейпов перед Classifier (w>100 или h>50)
- Дизайн-система: 12 колонок, Senior мыслит в колонках
- grid_calculator отложен — будем строить полноценный LayoutEngine (ФАЗА 4.5)
- header_type на уровне презентации (из Strategy), не per-slide
- 2 типа заголовков: fixed (прибит сверху) / floating (плавает с контентом)
- 2 стиля: strict, soft
- 4 режима презентаций: formal, technical, sales, report
- 6 типов объектов: heading, text, card, table, chart, visual
- Промпты модульные: core_rules + style + header + card/patterns
- system_instruction для всех агентов — rules отдельно от данных
- Strategy Director — 1 вызов flash на всю презу (~$0.002), даёт единый стиль
- Strategy кэшируется отдельно (temp/cache/strategy.json)
- Classifier: батч до 20 слайдов (без vision) или поштучно (с vision)
- Senior: батч до 10 слайдов
- Junior: async параллельно до 5 слайдов
- Кэш между агентами: temp/cache/ (strategy, classification, layout_plan, svg)
- Orchestrator поддерживает: --no-cache, --no-vision, --no-batch, --slides=0,1,2, --accent=#XXXXXX
- Junior-программист (Continue + Gemini Ctrl+I) больше НЕ используется — Tech Lead пишет код целиком, Operator копирует
- Тесты только на 1 слайде (--slides=0), полная прога только когда стабильно

## ⚡ Оптимизации сделанные
- system_instruction — rules грузятся 1 раз, не в каждый промпт
- Батчинг Classifier + Senior — меньше API вызовов
- Async Junior — 5 слайдов параллельно
- Кэш — повторный запуск не тратит токены
- Strategy Director — 1 вызов на всю презу вместо per-slide решений
- Мульти-изображения в одном запросе для Strategy (5-20 картинок за вызов)