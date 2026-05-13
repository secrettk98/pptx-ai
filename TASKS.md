# PPTX-AI — Task Tracker

## ✅ Завершено

### Фазы 0-4.4 (база + агенты + Strategy Director)
Парсер, контракты, AI-агенты, миграция на Vertex AI, Strategy Director.

### Фаза 4.5: Architect
Объединили Classifier + Senior → Architect (1 flash вызов).

### Фаза 4.6: LayoutEngine v4 + SVG Renderer v4 + Orchestrator v4
Самописный layout + SVG рендерер. Работали, но метрики текста были приблизительные.

### Фаза 4.7: LayoutEngine v5 (stretchable + Pillow)
- stretchable (Taffy) — промышленный flex/grid
- Pillow + Inter TTF — точные метрики (1/64 px)
- text_metrics.py: measure, wrap, fit_height, measure_block, truncate, baseline_offset
- RenderedText в BlockGeometry
- wrapper_nodes: координаты обёрток (card_x/y/w/h, cell_x/y/w/h) в extra
- Smoke-тесты: heading+text, 3 карточки, таблица ✅

### Фаза 4.7.1: SVG Renderer v5
- Тупой рендерер — только рисует по координатам из RenderedText
- Никаких wrap/truncate/измерений в рендерере
- accent_line — отдельный узел в layout, рендерер рисует по координатам
- baseline_offset через Pillow getmetrics()
- Центрирование текста в ячейках — в layout_engine
- Визуальные тесты: heading, карточки, таблица ✅

---

## 🔄 ТЕКУЩАЯ РАБОТА

### Фаза 4.8: Тестирование на реальных презентациях
- [ ] Прогон на 1 слайде (--slides=0) с реальной презентацией
- [ ] Прогон на 3-5 слайдах
- [ ] Визуальная проверка SVG в браузере
- [ ] Сквозной тест: PPTX → SVG → PPTX через SVG Engine
- [ ] Итерация качества (фиксы по результатам)

---

## 📋 Бэклог

### Фаза 5: Валидатор + Inspector
- [ ] postprocess/validator.py — bounds, overlap, text overflow
- [ ] agents/inspector.py — AI визуальная проверка (макс 2 итерации)

### Фаза 6: Реверс-модули
- [ ] reverse/chart_reverse.py (bar, pie, line)
- [ ] reverse/flowchart_reverse.py
- [ ] reverse/image_generator.py

### Фаза 7: Оптимизация
- [ ] pytest, метрики качества
- [ ] Цель: 80% успешных слайдов

---

## 🐛 Известные ограничения
- composition_schema B/C/D — пока всё как вертикальный стек (A)
- Header Type A — резервирует место, но не рендерит содержимое
- Иконки карточек — заглушка (буква в кружке)
- map_pipeline шаги 4-5 — заглушки