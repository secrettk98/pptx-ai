# PPTX-AI — Task Tracker

## ✅ Завершено
- Фазы 0-3: структура, контракты, парсер, конвертер, AI-агенты v1, SVG Engine
- Миграция на google.genai + Vertex AI
- designer.md обновлён, фикс markdown-мусора в SVG
- Map Pipeline ~80% (classifier, splitter, background, objects, assembler)
- Обогащённый парсер parse_pptx_rich() — позиции, стили, цвета, таблицы
- Ollama client (core/ollama_client.py) — готов для локальных моделей
- Vision classifier обновлён — возвращает visual_elements, has_map/chart/scheme
- Classifier (agents/classifier.py) — JSON_VISION + JSON_PARSED → JSON_FINAL ✅
- Контракты: SlideClassificationFinal, SlideGroup, ElementInfo, ColorPalette, ParsedShape, ParsedSlide и др.
- Промпты: prompts/classifier.md, prompts/vision_classifier.md (обновлены)

---

## 📋 ФАЗА 4.1: Рефакторинг под архитектуру v2

### Senior Designer
- [x] agents/senior_designer.py — LayoutPlan (rows, columns, grid_span)
- [x] prompts/senior_designer.md
- [x] models/contracts.py — LayoutPlan, RowInstruction, ColumnInstruction

### Classifier v2
- [x] agents/classifier.py — SlideClassificationV2 (6 объектов)
- [x] config/classifier.md — новая схема классификации
- [x] models/contracts.py — SlideClassificationV2, ClientConstraints
- [x] core/prompt_assembler.py — модульная сборка промптов
- [x] core/llm_normalize.py — нормализация ответов AI

### Junior Designer
- [ ] agents/junior_designer.py — SVG по инструкциям Senior'а
- [ ] prompts/junior_designer.md

### Валидатор
- [ ] postprocess/validator.py — XML валидность, bounds, текст не вылезает

### Inspection
- [ ] agents/inspector.py — визуальная проверка → возврат к Senior (макс 2)
- [ ] prompts/inspector.md

### Orchestrator v2
- [ ] core/orchestrator.py — новый пайплайн с циклом

---

## 📋 ФАЗА 4.2: Новая дизайн-система

### Дизайн-конфиги (готово)
- [x] config/core_rules.md — 12-колоночная сетка, 6 объектов
- [x] config/card.md — правила карточек
- [x] config/patterns.md — визуальные паттерны
- [x] config/modules_map.md — карта загрузки модулей
- [x] config/handoff.md — передача данных между агентами
- [x] config/headers/ — type_a, type_b, type_c
- [x] config/styles/ — strict.md, soft.md

### Junior Designer v2
- [ ] agents/junior_designer.py — переписать под LayoutPlan + prompt_assembler
- [ ] prompts/junior_designer.md — переписать под новые правила

### Валидатор
- [ ] postprocess/validator.py — проверка сетки, bounds, overlap, text overflow

### Inspection
- [ ] agents/inspector.py — AI визуальная проверка
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

## 📝 Решения принятые
- Локальные модели (Ollama) ненадёжны для структурированного JSON — используем Gemini
- Vision: простая роль (описание + флаги), группировку делает Classifier
- Фильтрация мелких шейпов перед Classifier (w>100 или h>50)
- Ollama client оставлен на будущее
- Дизайн-система: 12 колонок, Senior мыслит в колонках, Python конвертирует в пиксели
- 3 типа заголовков: A (rigid), B (floating), C (top) — выбирается один раз на презентацию
- 2 стиля: strict, soft — определяет Classifier
- 6 типов объектов: heading, text, card, table, chart, visual
- Промпты модульные: core_rules + style + header + card/patterns (по необходимости)