# PPTX-AI — Task Tracker

## ✅ Завершено
- **Фазы 0-4.4:** Базовый парсер, контракты, AI-агенты, миграция на Vertex AI, Strategy Director.
- **Фаза 4.6:** Самописный layout + SVG рендерер. Работали, но метрики текста были приблизительные.
- **Фаза 4.7:** LayoutEngine v5 (`stretchable` + `Pillow`) — промышленный flex/grid layout с точными метриками текста (1/64 px). Реализованы measure, wrap, baseline_offset.
- **Фаза 4.7.1:** SVG Renderer v5 — "тупой" отрисовщик по координатам из `RenderedText`.

## 🔄 В работе: Фаза 4.8 (Переход на 3-слойную архитектуру)
**Проблема:** В v4 Architect брал на себя всё (классификация, текст, верстка) и тонул в контексте, что приводило к overflow > 720px и галлюцинациям.
**Решение:** Разделение на Router -> Semantic Editor -> Spatial Architect -> Visual Modules.

- [x] Спроектировать 3-слойную когнитивную архитектуру.
- [x] Обновить `models/contracts.py` (внедрить 12-колоночную сетку `GridRow`/`GridBlock` и `hug/fill`).
- [ ] **(Текущий шаг)** Написать Промпт для Слоя 1 (Spatial Architect) с правилами бюджета строк и 12-колоночной сетки.
- [ ] Написать Промпт для Semantic Editor (Левое полушарие) с Golden Examples (Chain of Thought).
- [ ] Обновить `core/prompt_assembler.py` для динамической загрузки только нужных `.md` модулей вместо всех сразу.

## 📋 Бэклог

### Фаза 5: Интеграция модулей Слоя 2
- [ ] Интеграция API иконок (поиск SVG по `icon_concept`).
- [ ] Модуль Chart (генерация JSON для создания нативных графиков PPTX).
- [ ] Подготовка SVG-заготовок для Pattern (SWOT, Timeline и т.д.).
- [ ] Разработка логики Map Redesigner (через `cv2` / LLM Vision).

### Фаза 6: Валидация и QA
- [ ] Слой 2.5: Python Validator (`postprocess/validator.py` — fast-fail retry при overflow > 720px).
- [ ] Слой 3: AI Inspector (`agents/inspector.py` — визуальная и семантическая проверка).

### Фаза 7: Оптимизация
- [ ] Настройка метрик качества и `pytest` (цель: 80% идеальных слайдов без правок руками).