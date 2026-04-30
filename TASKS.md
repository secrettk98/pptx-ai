# PPTX-AI — Task Tracker

## ✅ Завершено (история)
- [x] Исследование решений → выбран PPT Master + Gemini
- [x] Design System v1.0 → v2.0
- [x] Тест AI-анализа структуры (35% без примеров, 65% с RAG)
- [x] Тест SVG → PPTX
- [x] Архитектура + многоагентная система
- [x] Vision-тест 7 моделей → выбран Gemini 2.5 Flash
- [x] Финансовая модель + конкурентный анализ
- [x] layout_code.md + design_code_style1.md (документы есть, в репо ещё не лежат)
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

## 📋 ФАЗА 0: Рефакторинг и каркас (СЕЙЧАС, 1-2 дня)

### Структура и контракты
- [ ] Создать целевую структуру папок: core/, parsers/, agents/, ppt_master/, postprocess/, models/, prompts/, tests/
- [ ] Создать models/contracts.py — все Pydantic-модели контрактов между агентами
- [ ] Создать core/llm_client.py — единая обёртка для Gemini (кэш + retry + метрики)
- [ ] Создать core/config.py — централизованные настройки (модели, таймауты, пути)
- [ ] Создать core/logger.py — единое логирование
- [ ] Создать core/orchestrator.py — скелет с заглушками всех 15 шагов
- [ ] Переписать main.py как тонкую обёртку над orchestrator (старый сломан)
- [ ] Дополнить requirements.txt: opencv-python, scikit-image, pillow, pydantic, lxml, pdf2image, graphviz
- [ ] Перенести существующие промпты (CLASSIFIER_PROMPT и др.) в prompts/*.md

---

## 📋 ФАЗА 1: Базовый пайплайн без AI (3-5 дней)

### Парсер PPTX
- [ ] parsers/pptx_parser.py — обёртка над pptxtojson (subprocess) ИЛИ python-pptx
- [ ] Pydantic-модель PresentationStructure
- [ ] Тест на projects/test_map/test_maps.pptx

### Конвертер слайдов в JPG
- [ ] parsers/slide_renderer.py — LibreOffice headless → PDF → JPG (pdf2image)
- [ ] Альтернатива на Windows: проверить установку LibreOffice
- [ ] Тест: PPTX → набор JPG в temp/

### Точка входа
- [ ] core/orchestrator.py — реальный вызов парсер → конвертер
- [ ] CLI: python main.py input.pptx --accent #0066CC

---

## 📋 ФАЗА 2: AI-агенты (5-7 дней)

### Vision-классификатор
- [ ] agents/vision_classifier.py — Gemini 2.5 Flash + промпт
- [ ] Pydantic SlideClassification (slide_type, has_chart, has_map, has_flowchart, has_table)
- [ ] prompts/vision_classifier.md
- [ ] Тест на 3 эталонных PPTX

### Мозг (Арт-директор)
- [ ] agents/brain.py — Gemini 3.1 Pro
- [ ] Уровень 1: саммари → PresentationStrategy
- [ ] Уровень 2: пачки слайдов → SlideBrief[]
- [ ] CoT "30 секунд спикера" + надстройки по типу презентации
- [ ] prompts/brain_level1.md, brain_level2.md
- [ ] Pydantic PresentationStrategy, SlideBrief
- [ ] Тест на 3 эталонных PPTX

### Дизайнер
- [ ] agents/designer.py — Gemini 3.1 Flash
- [ ] Промпт + design_code_style1.md + few-shot из catalog.json
- [ ] prompts/designer.md
- [ ] Pydantic DesignedSlide
- [ ] Catalog.json — стартовая библиотека из 10-20 эталонных слайдов
- [ ] Тест: бриф → SVG

### Подборщик и Тестер шаблонов
- [ ] agents/template_matcher.py — поиск в catalog.json
- [ ] Логика "если совпадение >0.85 → жёсткий шаблон ($0), иначе → Дизайнер"

---

## 📋 ФАЗА 3: PPT Master — критичный блокер

⚠️ **Внимание:** PPT Master упомянут в документации как готовый, но в репозитории его нет. Это БЛОКЕР для финальной сборки.

- [ ] Найти/восстановить svg_to_pptx.py и finalize_svg.py
- [ ] ИЛИ написать с нуля: SVG → нативные shapes через python-pptx
- [ ] Поддержка элементов: rect, circle, line, path, text, image, use
- [ ] Тест: эталонный SVG → PPTX → визуальное соответствие

---

## 📋 ФАЗА 4: Постобработка и Инспектор

### Постобработчик PPTX
- [ ] postprocess/pptx_polish.py — паддинги, скругления через python-pptx

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
- [ ] reverse/flowchart_reverse.py — Vision AI → JSON-граф → Graphviz → SVG → PPT Master
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

### Прочее
- [ ] Жёсткие шаблоны под типовые слайды (титул, разделитель, контакты)
- [ ] Failover между моделями
- [ ] Локальные модели для корпоратов (DPA, конфиденциальность)
- [ ] Маркетинг
- [ ] Иконки: автоподбор из Noun Project / Tabler Icons

---

## 🐛 Известные баги (актуальные)
- [ ] main.py сломан — импортирует несуществующие processors/* (исправится в Фазе 0)
- [ ] requirements.txt неполный (исправится в Фазе 0)
- [ ] map_pipeline.py: шаги 4-5 — TODO заглушки (исправится в Фазе 5)
- [ ] PPT Master отсутствует в репозитории (Фаза 3)
- [ ] SVG text не переносится автоматически (выход за карточки) — для постобработки
- [ ] Скругления пропадают при разгруппировке shape — для постобработки
- [ ] Дефолтные паддинги PowerPoint — для постобработки
- [ ] data-icon без finalize_svg.py — для PPT Master
- [ ] Внешние изображения не находятся при сборке — для PPT Master

---

## ❌ Что НЕ работает (проверено, НЕ повторять)
Полный список — в CLAUDE.md, раздел "Что НЕ работает".

Основные провалы:
- Векторизация маршрутов с пересечениями (skan, trace_skeleton, per-route extraction, эрозия, Gemini App) — отложено в R&D
- Большинство классических CV-подходов между картами разных стилей (ORB, SIFT, matchTemplate, аффинное преобразование) — работает только Edge Matching
- vtracer, pypotrace, EasyOCR, keras-ocr на Windows — не ставятся
- pip install trace-skeleton — нужен Visual Studio Build Tools

---

## 📊 Эталонные тестовые файлы
- SmartGas.pptx (7 сл, оранжевый)
- Welcome.pptx (18 сл, синий)
- AI UDP.pptx (9 сл, синий)
- projects/test_map/test_maps.pptx (3 сл, для тестов карт)
- projects/test_map/test_maps_grouped.pptx (1 сл со сгруппированной картой)