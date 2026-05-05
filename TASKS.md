# PPTX-AI — Task Tracker

## ✅ Завершено
- Фазы 0-3: структура, контракты, парсер, конвертер, AI-агенты v1, SVG Engine
- Миграция на google.genai + Vertex AI
- designer.md обновлён, фикс markdown-мусора в SVG
- Map Pipeline ~80% (classifier, splitter, background, objects, assembler)

---

## 📋 ФАЗА 4.1: Рефакторинг под архитектуру v2

### Classifier
- [ ] agents/classifier.py — JSON_VISION + JSON_PARSED → JSON_FINAL
- [ ] prompts/classifier.md
- [ ] models/contracts.py — SlideClassificationFinal

### Senior Designer
- [ ] agents/senior_designer.py — концепция, шаблон, инструкции
- [ ] prompts/senior_designer.md
- [ ] models/contracts.py — DesignInstruction

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
- [ ] gemini-3.1-flash-lite-preview 404 в Vertex AI
- [ ] map_pipeline шаги 4-5 заглушки
