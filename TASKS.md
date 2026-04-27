# PPTX-AI — Task Tracker

## Завершено (история)
- [x] Исследование решений — выбран PPT Master + Gemini
- [x] Design System v1.0 → v2.0 — три документа
- [x] Тест AI-анализа структуры — 35% без примеров, 65% с RAG
- [x] Тест SVG → PPTX — конвейер работает
- [x] Архитектура + многоагентная система — утверждены
- [x] Vision-тест — 7 моделей, выбран Gemini 2.5 Flash
- [x] Финансовая модель + конкурентный анализ
- [x] layout_code.md + design_code_style1.md
- [x] Промпт Мозга + тест Мозг+Дизайнер (3 слайда, работает)
- [x] Model routing, Pydantic в стек
- [x] Киллер-фича — реверс-инжиниринг через Graphviz/Matplotlib

## Фаза 1: Доказательство киллер-фич (ТЕКУЩАЯ)

### Карты — Map Pipeline v2.1
- [x] Gemini Vision → JSON (регион, города, маршруты, зоны) — РАБОТАЕТ
- [x] Nominatim + viewbox → геокодирование → GPS — РАБОТАЕТ
- [x] Mapbox Static Images → чистая подложка — РАБОТАЕТ
- [x] OpenCV HSV (S≥80) → маски маршрутов — РАБОТАЕТ
- [x] Skan + Douglas-Peucker → SVG polyline — РАБОТАЕТ
- [x] map_classifier.py — Gemini → тип карты 1-13 — РАБОТАЕТ
- [x] map_layer_splitter.py — PPTX → background + objects — РАБОТАЕТ
- [x] map_pipeline.py — оркестратор — РАБОТАЕТ (шаги 4-5 заглушки)
- [x] map_background.py — mapbox + keep стратегии — РАБОТАЕТ
- [x] Исследование совмещения карт — найден рабочий подход (Nominatim bbox + 5% padding)
- [ ] map_objects_redesign.py — пересадка объектов по GPS↔пиксель формуле ← СЛЕДУЮЩИЙ
- [ ] map_vectorizer.py — рефакторинг vectorize_clean.py
- [ ] map_assembler.py — финальная сборка
- [ ] Обновить map_classifier.py и map_background.py: модель → gemini-3.1-flash-lite-preview
- [ ] Тест на 20-30 слайдах — цель 80%

### Диаграммы — НЕ НАЧАТО
- [ ] Vision → данные → Matplotlib/python-pptx → нативный график

### Блок-схемы — НЕ НАЧАТО
- [ ] Vision → JSON-граф → Graphviz → SVG → PPT Master

### Прочее
- [ ] Иконки: автоподбор из Noun Project / Tabler Icons
- [ ] AI-изображения: тест Nano Banana 2

## Фаза 2: Пайплайн

### Парсер + Vision
- [ ] pptxtojson JS + Python-обёртка
- [ ] PPTX → JPG (LibreOffice headless)
- [ ] Vision-классификатор
- [ ] Динамический контроль цвета

### Центральный мозг
- [ ] Промпт (Gemini 3.1 Pro)
- [ ] Батчинг
- [ ] Подборщик шаблонов + catalog.json
- [ ] Few-shot библиотека

### Генерация
- [ ] Дизайнер-верстальщик (SVG)
- [ ] Художник (Nano Banana 2)
- [ ] Полный пайплайн PPTX → PPTX

### Качество
- [ ] Инспектор + good_slide_rules.md
- [ ] Постобработка PPTX
- [ ] Pydantic-модели для всех агентов
- [ ] Прогон 3 эталонов

## Фаза 3: Веб-интерфейс
- [ ] Фронтенд + загрузка + оплата + деплой

## Фаза 4+: Будущее
- [ ] Жёсткие шаблоны
- [ ] Failover
- [ ] Маркетинг
- [ ] Локальные модели для корпоратов

## Известные баги
- [ ] SVG text не переносится (выход за карточки)
- [ ] Скругления пропадают при разгруппировке
- [ ] Дефолтные паддинги PowerPoint
- [ ] data-icon без finalize_svg.py
- [ ] Внешние изображения не найдены при сборке

## Эталонные файлы
- SmartGas.pptx (7сл, оранжевый) | Welcome.pptx (18сл, синий) | AI UDP.pptx (9сл, синий)
