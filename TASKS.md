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
- [x] Gemini Vision → JSON (регион, города, маршруты, зоны)
- [x] Nominatim + viewbox → геокодирование → GPS
- [x] Mapbox Static Images → чистая подложка
- [x] OpenCV HSV (S≥80) → маски маршрутов (для простых случаев)
- [x] map_classifier.py
- [x] map_layer_splitter.py (с crop fix + разгруппировкой)
- [x] map_pipeline.py
- [x] map_background.py — Edge Matching + точный bbox
- [x] map_objects_redesign.py
- [x] map_assembler.py (без дублирующего crop)
- [x] Кэширование geo_cache.json
- [x] Nominatim двухпроходный
- [x] CROP FIX: подложка обрезается по crop в splitter перед replace_background
- [x] Разгруппировка слайда — _iter_all_shapes рекурсивно разворачивает группы
- [R&D, отложено] map_vectorizer.py — векторизация маршрутов с пересечениями.
  Провалились: skan, trace_skeleton (LingDong), гибридный подход с общей маской,
  per-route extraction со склейкой по углам, эрозия маски, Vision LLM (Gemini App
  и на шумной карте, и на чистой HSV-маске). Корни: на пересечениях скелетон
  искривляется, Gemini ставит точки с погрешностью 100+px. План на R&D после MVP:
  SAM 2 + HSV + skeleton-tracing комбо, либо специализированный U-Net на синтетике,
  либо Gemini 3.1 Pro через API (не через App). Пока тип карты 6 (сложный растр)
  использует fallback Nano Banana 2.
- [ ] Карты без подписей — region_hint от Мозга
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

## Что НЕ работает (проверено, НЕ использовать)
- skeleton-tracing (LingDong) для маршрутов с пересечениями — кривизна на концах фрагментов
- Per-route extraction через гибрид общая-маска + голосование по цвету
- Эрозия маски перед скелетонизацией — изгибы остаются
- Gemini Pro в браузере (Gemini App) для извлечения polyline маршрутов — точки не совпадают (погрешность сотни пикселей)
- Подача чистой HSV-маски одного цвета в Gemini App — не помогает, точки всё равно неточные

## Эталонные файлы
- SmartGas.pptx (7сл, оранжевый) | Welcome.pptx (18сл, синий) | AI UDP.pptx (9сл, синий)