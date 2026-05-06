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

### Classifier
- [x] agents/classifier.py — JSON_VISION + JSON_PARSED → JSON_FINAL
- [x] prompts/classifier.md
- [x] models/contracts.py — SlideClassificationFinal
- [ ] Вынести фильтрацию мелких шейпов в classifier.py (сейчас в тесте)

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
- [ ] map_pipeline шаги 4-5 заглушки

## 📝 Решения принятые
- Локальные модели (Ollama) ненадёжны для структурированного JSON — используем Gemini
- Vision: простая роль (описание + флаги), группировку делает Classifier
- Фильтрация мелких шейпов перед Classifier (w>100 или h>50)
- Ollama client оставлен на будущее