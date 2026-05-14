# PPTX-AI — Task Tracker

## ✅ Завершено
- **Фазы 0-4.4:** Базовый парсер, AI-агенты, миграция на Vertex AI, Strategy Director.
- **Фаза 4.6:** Самописный layout + SVG рендерер.
- **Фаза 4.7:** LayoutEngine v5 (`stretchable` + `Pillow`) — промышленный flex/grid layout с точными метриками текста (1/64 px). Реализованы measure, wrap, baseline_offset.
- **Фаза 4.7.1:** SVG Renderer v5 — "тупой" отрисовщик по координатам из `RenderedText`.
- **Фаза 4.8 (Архитектура v5):**
  - Спроектирована 3-слойная когнитивная архитектура (Смысл -> Сетка -> Верстка).
  - Обновлен `models/contracts.py` (GridRow, GridBlock на 12 колонок, стратегии hug/fill).
  - Написан системный промпт для Semantic Editor (Слой 0) с Chain of Thought.
  - Написан системный промпт для Spatial Architect (Слой 1) с правилами бюджета строк и сетки.
  - Адаптирован `core/layout_engine.py` под новые контракты.

## 🔄 В работе: Завершение Фазы 4.8 (Пайплайн)
- [ ] **(Текущий шаг)** Обновить `core/prompt_assembler.py` (Слой 0.5) для динамической загрузки *только нужных* `.md` модулей из папки `config/` на основе `recommended_modules`, полученных от Semantic Editor.
- [ ] Интегрировать последовательный вызов (Semantic Editor -> Prompt Assembler -> Spatial Architect) в `core/orchestrator.py`.

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
- [ ] Настройка метрик качества и написание тестов `pytest` (цель: 80% идеальных слайдов без правок руками).