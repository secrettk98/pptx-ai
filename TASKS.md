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
- [x] core/grid_calculator.py — создан, но НЕ используется (Junior сам считает)
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

---

## 🔧 Нужно пофиксить (следующий чат)

### Качество SVG (ПРИОРИТЕТ 1)
- [ ] Junior не центрирует контент вертикально — огромные пустоты внизу
- [ ] Senior кладёт несколько карточек в 1 колонку grid_span=12 вместо 6+6
- [ ] Senior создаёт отдельный text-ряд для короткого подзаголовка (должен быть subtitle)
- [ ] Промпты junior_designer.md и senior_designer.md нуждаются в доработке
- [ ] grid_calculator.py — отключен от Junior, возможно удалить

### Чистка кода (ПРИОРИТЕТ 2)
- [ ] Удалить старые неиспользуемые контракты из contracts.py (DesignInstruction, BlockInstruction, SlideClassificationFinal и др.)
- [ ] Удалить мёртвый код из агентов
- [ ] Проверить все импорты — убрать неиспользуемые
- [ ] config.py: MODEL_INSPECTOR и MODEL_CHEAP указывают на gemini-3.1-flash-lite-preview (404 в Vertex)

---

## 📋 ФАЗА 4.3: Валидатор + Inspector
- [ ] postprocess/validator.py — XML валидность, bounds, overlap, text overflow
- [ ] agents/inspector.py — AI визуальная проверка → возврат к Senior (макс 2)
- [ ] prompts/inspector.md

---

## 📋 ФАЗА 5: Реверс-модули
- [ ] Подключить map_pipeline к оркестратору
- [ ] reverse/chart_reverse.py (bar, pie, line)
- [ ] reverse/flowchart_reverse.py (Graphviz)
- [ ] reverse/image_generator.py (Nano Banana 2)

---

## 📋 ФАЗА 6: Тесты и прогон
- [ ] Прогон SmartGas, Welcome, AI UDP
- [ ] pytest, метрики качества
- [ ] Цель: 80% успешных слайдов

---

## 🐛 Баги
- [ ] SVG word-wrap не всегда работает
- [ ] Постпроцессор скругляет ВСЕ Rectangle
- [ ] map_pipeline шаги 4-5 заглушки

---

## 📝 Решения принятые
- Локальные модели (Ollama) ненадёжны — используем Gemini
- Vision: простая роль, группировку делает Classifier
- Фильтрация мелких шейпов перед Classifier (w>100 или h>50)
- Дизайн-система: 12 колонок, Senior мыслит в колонках
- grid_calculator отключен — Junior сам рассчитывает позиции по правилам из промпта
- 3 типа заголовков: A (rigid), B (floating), C (top)
- 2 стиля: strict, soft
- 6 типов объектов: heading, text, card, table, chart, visual
- Промпты модульные: core_rules + style + header + card/patterns
- system_instruction для всех агентов — rules отдельно от данных
- Classifier: батч до 20 слайдов (без vision) или поштучно (с vision)
- Senior: батч до 10 слайдов
- Junior: async параллельно до 5 слайдов
- Кэш между агентами: temp/cache/ (classification, layout_plan, svg)
- Orchestrator поддерживает: --no-cache, --no-vision, --no-batch, --slides=0,1,2

## ⚡ Оптимизации сделанные
- system_instruction — rules грузятся 1 раз, не в каждый промпт
- Батчинг Classifier + Senior — меньше API вызовов
- Async Junior — 5 слайдов параллельно вместо последовательно
- Кэш — повторный запуск не тратит токены