# PPTX-AI — Task Tracker

## ✅ Завершено (история)
- [x] Исследование решений → выбран PPT Master + Gemini
- [x] Design System v1.0 → v2.0
- [x] Тест AI-анализа структуры (35% без примеров, 65% с RAG)
- [x] Тест SVG → PPTX
- [x] Архитектура + многоагентная система
- [x] Vision-тест 7 моделей → выбран Gemini 2.5 Flash
- [x] Финансовая модель + конкурентный анализ
- [x] layout_code.md + design_code_style1.md (в config/)
- [x] Промпт Мозга + тест Мозг+Дизайнер на 3 слайдах
- [x] Model routing
- [x] Map Pipeline — реверс карт (~80%):
  - [x] map_classifier.py
  - [x] map_layer_splitter.py (с crop fix + разгруппировкой)
  - [x] map_background.py (Edge Matching + точный bbox)
  - [x] map_objects_redesign.py
  - [x] map_assembler.py (без дублирующего crop)
  - [x] Кэширование geo_cache.json
  - [x] Nominatim двухпроходный

## 🎯 Текущая стратегия: "Тонкий вертикальный срез" MVP
Прошить ВСЕ 15 шагов пайплайна на простых текстовых слайдах, потом подключать реверс-модули по одному. Цель — увидеть как клиент получает редизайн end-to-end за 2-3 недели.

---

## 📋 ФАЗА 0: Рефакторинг и каркас ✅ ЗАВЕРШЕНА

### Структура и контракты
- [x] Создать целевую структуру папок: core/, parsers/, agents/, svg_engine/, postprocess/, models/, prompts/, tests/
- [x] Создать models/contracts.py — все Pydantic-модели контрактов между агентами
- [x] Создать core/llm_client.py — единая обёртка для Gemini (retry + экспоненциальная задержка)
- [x] Создать core/config.py — централизованные настройки (модели, таймауты, пути) + load_dotenv()
- [x] Создать core/logger.py — единое логирование
- [x] Создать core/orchestrator.py — скелет с заглушками всех 15 шагов + очистка temp/
- [x] Переписать main.py как тонкую обёртку над orchestrator (argparse: input, --accent, --mode)
- [x] Дополнить requirements.txt: opencv-python, scikit-image, pillow, pydantic, lxml, pdf2image, graphviz, matplotlib, python-dotenv, requests
- [x] Перенести CLASSIFIER_PROMPT в prompts/map_classifier.md
- [x] Удалить мусор: assets/test_slide.json, reverse/vectorize_clean.py

---

## 📋 ФАЗА 1: Базовый пайплайн без AI ✅ ЗАВЕРШЕНА

### Парсер PPTX
- [x] parsers/pptx_parser.py — python-pptx с рекурсивным обходом групп (_iter_all_shapes)
- [x] Pydantic-модель PresentationStructure + SlideInfo
- [x] Тест на projects/test_map/test_maps.pptx (3 слайда, 77 shapes на слайде 0)

### Конвертер слайдов в JPG
- [x] parsers/slide_renderer.py — LibreOffice headless → PDF → JPG (pdf2image)
- [x] Установлен LibreOffice 26.2 + Poppler 25.12 (добавлен в PATH навсегда)
- [x] Тест: PPTX → 3 JPG в temp/slides/

### Точка входа
- [x] core/orchestrator.py — реальный вызов парсер → конвертер
- [x] CLI: python main.py input.pptx --accent #0066CC --mode pitch

---

## 📋 ФАЗА 2: AI-агенты ✅ ЗАВЕРШЕНА

### Vision-классификатор
- [x] agents/vision_classifier.py — Gemini 2.5 Flash + промпт
- [x] Pydantic SlideClassification (slide_type, has_chart, has_map, has_flowchart, has_table)
- [x] prompts/vision_classifier.md
- [x] classify_all() с time.sleep(3) между вызовами (лимит бесплатной модели)
- [x] Тест: slide_0=map, slide_1=mixed(map), slide_2=mixed(map) — правильно

### Мозг (Арт-директор)
- [x] agents/brain.py — get_strategy() + get_briefs()
- [x] Уровень 1: саммари → PresentationStrategy
- [x] Уровень 2: пачки слайдов → SlideBrief[]
- [x] CoT "30 секунд спикера" + надстройки по типу презентации
- [x] prompts/brain_level1.md, brain_level2.md
- [x] Языковая адаптация (IMPORTANT: respond in same language as content)
- [x] Тест: стратегия + брифы для 3 слайдов — работает

### Дизайнер
- [x] agents/designer.py — генерация SVG по брифу
- [x] prompts/designer.md — подключены layout_code.md + design_code_style1.md
- [x] Pydantic DesignedSlide
- [x] FALLBACK_SVG при ошибке
- [ ] Catalog.json — стартовая библиотека эталонных слайдов (TODO)
- [ ] Тест на 3 эталонных PPTX (качество нестабильно)

### Подборщик и Тестер шаблонов
- [ ] agents/template_matcher.py — поиск в catalog.json
- [ ] Логика "если совпадение >0.85 → жёсткий шаблон ($0), иначе → Дизайнер"

---

## 📋 ФАЗА 3: SVG Engine ✅ ЗАВЕРШЕНА

- [x] svg_engine/ — скопирован из PPT Master (MIT лицензия, github.com/hugohe3/ppt-master)
- [x] 13 файлов: drawingml_converter, drawingml_elements, drawingml_paths, drawingml_styles, drawingml_context, drawingml_utils, pptx_builder, pptx_cli, pptx_dimensions, pptx_media, pptx_notes, pptx_narration, pptx_slide_xml
- [x] svg_engine/convert.py — обёртка svg_to_pptx() для оркестратора
- [x] Тест: SVG → нативный PPTX, все элементы кликабельные и редактируемые
- [x] TextBox создаётся правильно (txBox="1", noFill, lIns/tIns/rIns/bIns="0")

---

## 📋 ФАЗА 4: Постобработка и Инспектор — ⚠️ В РАБОТЕ

### Постпроцессор SVG
- [x] postprocess/svg_fix.py — snap_to_grid, clamp в рабочую область, выравнивание карточек
- [ ] Word-wrap для длинного текста в SVG (текст выходит за карточки)
- [ ] Умнее выравнивание: одинаковые ширины карточек в ряду

### Постпроцессор PPTX
- [x] postprocess/pptx_fix.py — скругления Rectangle→roundRect(5%), паддинги Pt(0), шрифт Google Sans
- [x] Рекурсивный обход групп (_iter_all_shapes)
- [x] TextBox НЕ скругляется (откат roundRect→rect для TextBox)
- [ ] Умная логика скруглений (не все Rectangle нужно скруглять — только карточки с цветным фоном)

### Инспектор
- [ ] agents/inspector.py — Gemini 2.5 Flash
- [ ] Логика: PPTX → JPG → проверка → если плохо, возврат к Дизайнеру (max 2 итерации)
- [ ] prompts/inspector.md + good_slide_rules.md
- [ ] Pydantic InspectionResult

### Художник (опционально на этом этапе)
- [ ] agents/artist.py — Nano Banana 2 через Vertex AI
- [ ] Тест на 1-2 слайдах

---

## 📋 ФАЗА 5: Подключение реверс-модулей

### Подключение карт к оркестратору
- [ ] Дописать map_pipeline.py: шаги 4-5 (вызовы map_background, map_objects_redesign, map_assembler)
- [ ] Интегрировать в core/orchestrator.py роутинг "если has_map → reverse.map_pipeline"
- [ ] Перенести reverse/ модули под общий стиль контрактов (Pydantic-модели)

### Реверс диаграмм
- [ ] reverse/chart_reverse.py — Vision AI → данные → нативный chart через python-pptx
- [ ] Поддержка: bar, pie, line
- [ ] prompts/chart_extractor.md

### Реверс блок-схем
- [ ] reverse/flowchart_reverse.py — Vision AI → JSON-граф → Graphviz → SVG → SVG Engine
- [ ] prompts/flowchart_extractor.md
- [ ] Установка Graphviz (системная зависимость)

---

## 📋 ФАЗА 6: Полный прогон и тесты
- [ ] Прогон 3 эталонных файлов: SmartGas.pptx, Welcome.pptx, AI UDP.pptx
- [ ] Покрытие тестами через pytest (юниты на агенты, интеграционные на оркестратор)
- [ ] Метрики качества: время, стоимость, успешность
- [ ] Цель: 80% успешных слайдов из коробки

---

## 📋 ФАЗА 7: Веб-интерфейс
- [ ] Бэкенд (FastAPI): загрузка PPTX, очередь задач, скачивание
- [ ] Фронтенд (минимальный): загрузка + прогресс + результат
- [ ] Оплата (Stripe / ЮKassa)
- [ ] Деплой (VPS + Docker)

---

## 📋 ФАЗА 8: R&D и улучшения (после MVP)

### Карты
- [ ] Карты без подписей — region_hint от Мозга (параметр в map_background.py)
- [ ] map_vectorizer.py — векторизация маршрутов с пересечениями:
  - Подходы для исследования: SAM 2 + HSV + skeleton-tracing комбо, специализированный U-Net на синтетических данных, Gemini 3.1 Pro через API (не Gemini App)
  - Текущий fallback для типа 6: Nano Banana 2

### Дизайн и качество
- [ ] Самообучающаяся система шаблонов из примеров в интернете
- [ ] Подключить API бесплатных иконок (Tabler Icons / Noun Project)
- [ ] Научить Дизайнера вставлять SVG-иконки

### Прочее
- [ ] Жёсткие шаблоны под типовые слайды (титул, разделитель, контакты)
- [ ] Failover между моделями
- [ ] Локальные модели для корпоратов (DPA, конфиденциальность)
- [ ] Маркетинг
- [ ] Переход google.generativeai → google.genai

---

## 🔥 БЛОКЕРЫ (решить первыми)

### 1. Промпт Дизайнера слишком длинный
layout_code.md + design_code_style1.md = ~12KB → бесплатная модель обрезает SVG на выходе.
Варианты решения:
- [ ] Сжать документы до самого важного (убрать описания, оставить числа)
- [ ] Перейти на платную модель с большим контекстом
- [ ] Разделить: AI выбирает layout → генерит SVG с правилами только этого layout
- [ ] Кэшировать: типовые layouts → готовые SVG-скелеты, AI заполняет контент

### 2. Качество дизайна нестабильно
AI не соблюдает сетку, текст выходит за карточки, выравнивание кривое, стиль "как у Gamma".
Стратегия (обсуждено):
- Подход А (выбран): Постпроцессор-сетка — AI генерит свободно, Python выравнивает
- Подход Б (отвергнут): JSON-скелеты с координатами — слишком негибкий
- design_code_style1.md с точными числами — подключен, но промпт обрезается
- Few-shot эталоны — только для типовых (титул, разделитель)
- R&D: самообучение из примеров в интернете

### 3. google.generativeai deprecated
- [ ] Перейти на google.genai SDK (предупреждение при каждом запуске)

---

## 🐛 Известные баги (актуальные)
- [ ] Промпт Дизайнера обрезается на бесплатной модели (SVG не догенерируется)
- [ ] SVG text не переносится автоматически (выход за карточки)
- [ ] Постпроцессор скругляет ВСЕ Rectangle (нужна умная фильтрация по цвету фона)
- [ ] time.sleep(3) между API-вызовами (лимит бесплатной модели → прогон ~8 мин)
- [ ] google.generativeai deprecated warning при каждом запуске
- [ ] map_pipeline.py: шаги 4-5 — TODO заглушки (Фаза 5)
- [ ] data-icon без finalize_svg.py (для SVG Engine)
- [ ] Внешние изображения не находятся при сборке SVG Engine

---

## ❌ Что НЕ работает (проверено, НЕ повторять)
Полный список — в CLAUDE.md, раздел "Что НЕ работает".

Основные провалы:
- Векторизация маршрутов с пересечениями (skan, trace_skeleton, per-route extraction, эрозия, Gemini App) — отложено в R&D
- Большинство классических CV-подходов между картами разных стилей (ORB, SIFT, matchTemplate, аффинное преобразование) — работает только Edge Matching
- vtracer, pypotrace, EasyOCR, keras-ocr на Windows — не ставятся
- pip install trace-skeleton — нужен Visual Studio Build Tools
- Подход Б для сетки (JSON-скелеты) — отвергнут как слишком негибкий

---

## 📊 Эталонные тестовые файлы
- SmartGas.pptx (7 сл, оранжевый)
- Welcome.pptx (18 сл, синий)
- AI UDP.pptx (9 сл, синий)
- projects/test_map/test_maps.pptx (3 сл, для тестов карт)
- projects/test_map/test_maps_grouped.pptx (1 сл со сгруппированной картой)