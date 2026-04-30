# PPTX-AI — Project Context

## Что это за продукт
B2B AI-сервис редизайна и генерации презентаций PowerPoint.
- Режим 1 (редизайн): клиент загружает PPTX + акцентный цвет → AI анализирует → генерирует SVG → собирает нативный редактируемый PPTX
- Режим 2 (генерация): клиент даёт текст/документ + акцент → AI создаёт презентацию с нуля
- Цена клиенту $3-10 за презентацию, себестоимость ~$0.50-0.85, маржа 70-85%

## Главный принцип
LLM — мозг (анализ, выбор layout, бриф). Python — руки (парсинг, постобработка, сборка). Никаких PNG/PDF в финале — только редактируемые нативные элементы PowerPoint.

## Киллер-фича
Реверс-инжиниринг сложных элементов:
- Карты → Map Pipeline (13 типов, 7 модулей) → нативный PPTX
- Диаграммы → Vision AI → данные → нативный график python-pptx
- Блок-схемы → Vision AI → граф → Graphviz → SVG → PPTX

## Текущее состояние проекта (АПРЕЛЬ 2026)

### Что реально работает (end-to-end)
Полный пайплайн редизайна запускается: `python main.py input.pptx --accent "#0066CC" --mode pitch`
1. ✅ Парсер PPTX (с рекурсивным обходом групп)
2. ✅ Конвертер слайдов в JPG (LibreOffice + Poppler + pdf2image)
3. ✅ Vision-классификатор (Gemini 2.5 Flash)
4. ✅ Мозг/Арт-директор (стратегия + брифы)
5. ✅ Дизайнер (SVG по брифу + layout_code.md + design_code_style1.md)
6. ✅ SVG Engine (PPT Master, MIT) → нативный PPTX
7. ✅ Постпроцессоры SVG + PPTX (сетка, скругления, паддинги, шрифты)
8. ✅ Реверс карт: ~80% (не подключено к оркестратору)

### Структура репозитория
pptx-ai/ ├── core/ # orchestrator.py, config.py, logger.py, llm_client.py ├── parsers/ # pptx_parser.py, slide_renderer.py ├── agents/ # brain.py, designer.py, vision_classifier.py ├── reverse/ # map_pipeline.py, map_classifier.py, map_layer_splitter.py, │ # map_background.py, map_objects_redesign.py, map_assembler.py, │ # trace_skeleton.py ├── svg_engine/ # drawingml_.py, pptx_.py, convert.py (из PPT Master, MIT) ├── postprocess/ # svg_fix.py, pptx_fix.py ├── models/ # contracts.py (Pydantic-модели контрактов) ├── prompts/ # vision_classifier.md, brain_level1.md, brain_level2.md, │ # designer.md, map_classifier.md ├── config/ # layout_code.md, design_code_style1.md ├── assets/ # SVG-шаблоны, иконки (TODO) ├── projects/ # тестовые данные ├── tests/ # pytest (TODO) ├── main.py # CLI точка входа → core/orchestrator.py ├── requirements.txt # все зависимости ├── CLAUDE.md # этот файл └── TASKS.md # трекер задач

### Зависимости окружения (не в pip)
- LibreOffice 26.2 — конвертация PPTX → PDF (C:\Program Files\LibreOffice\program\soffice.exe)
- Poppler 25.12 — конвертация PDF → JPG (добавлен в PATH)

## Команда (3 роли)
- **Tech Lead (Claude)** — продумывает логику, алгоритмы, архитектуру
- **Operator (Алишер)** — Python-новичок, открывает файлы, нажимает кнопки
- **Junior Developer (Continue + Gemini)** — ИИ-плагин в VS Code (Ctrl+I), пишет код

### Формат ответа Техлида:
1. 📁 Файл: точное имя
2. 🖱️ Действие для Оператора
3. 🤖 Промпт для Джуниора (Ctrl+I)
4. 🧠 Примечание (опционально)

### Правила
- Экономим токены — не вставляем большие куски кода в чат
- Для быстрых тестов: temp_check.py → запустили → удалили
- Бюджет чата: 200000 токенов (считать в конце каждого сообщения)
- Запуск модулей: `python -m module.name`
- PowerShell: команды по одной, без &&

## Рабочее окружение
- OS: Windows, терминал PowerShell
- IDE: VS Code + Continue (Junior Developer)
- Python 3.14, venv: `./venv/Scripts/Activate.ps1`
- Python SDK: google-generativeai 0.8.6 (deprecated, нужен переход на google.genai)
- Тестовая модель: gemini-3.1-flash-lite-preview (бесплатно, но лимиты 5 RPM)
- Mapbox token: переменная MAPBOX_ACCESS_TOKEN
- Gemini key: переменная GEMINI_API_KEY (из .env через load_dotenv)

## Стек
- **Парсинг PPTX:** python-pptx (с рекурсивным обходом групп)
- **Конвертация:** LibreOffice headless → PDF → JPG (pdf2image + Poppler)
- **AI:** google-generativeai (Gemini 2.5 Flash, 3.1 Flash, 3.1 Pro)
- **SVG → PPTX:** svg_engine (из PPT Master, MIT лицензия)
- **Изображения:** Pillow, OpenCV, scikit-image, NumPy
- **Карты:** Mapbox Static Images API, Nominatim
- **Валидация:** Pydantic
- **Конфиг:** python-dotenv, core/config.py

## AI-агенты

| Агент | Модель | Файл | Статус |
|-------|--------|------|--------|
| Парсер | python-pptx | parsers/pptx_parser.py | ✅ |
| Конвертер | LibreOffice+pdf2image | parsers/slide_renderer.py | ✅ |
| Vision-классификатор | Gemini 2.5 Flash | agents/vision_classifier.py | ✅ |
| Мозг (Арт-директор) | Gemini 3.1 Pro | agents/brain.py | ✅ |
| Дизайнер | Gemini 3.1 Flash | agents/designer.py | ✅ (но качество нестабильно) |
| SVG Engine | Python | svg_engine/convert.py | ✅ |
| Постпроцессор SVG | Python | postprocess/svg_fix.py | ✅ |
| Постпроцессор PPTX | Python | postprocess/pptx_fix.py | ✅ |
| Инспектор | Gemini 2.5 Flash | agents/inspector.py | ❌ TODO |
| Художник | Nano Banana 2 | agents/artist.py | ❌ TODO |
| Реверс-картограф | Map Pipeline | reverse/map_pipeline.py | ⚠️ 80%, не подключён |
| Реверс-диаграмм | Vision AI | reverse/chart_reverse.py | ❌ TODO |
| Реверс-схем | Vision AI + Graphviz | reverse/flowchart_reverse.py | ❌ TODO |
| Подборщик шаблонов | Gemini 2.5 Flash | agents/template_matcher.py | ❌ TODO |

## Утверждённый пайплайн (15 шагов)
1. Клиент загружает PPTX + акцент + режим
2. Парсер → PresentationStructure ✅
3. Конвертер → slide_X.jpg ✅
4. Vision-классификатор → SlideClassification ✅
5. Мозг → PresentationStrategy + SlideBrief[] ✅
6. Подборщик шаблонов → few-shot (TODO)
7. Тестер шаблонов → жёсткий шаблон если >0.85 (TODO)
8. Дизайнер → SVG ✅
9. Реверс-инжиниринг (TODO подключение)
10. Художник → AI-изображения (TODO)
11. Постобработка SVG ✅
12. SVG Engine → PPTX ✅
13. Постобработка PPTX ✅
14. Инспектор (TODO)
15. Клиент скачивает

## Контракты (models/contracts.py)
- PresentationStructure, SlideInfo
- SlideClassification
- PresentationStrategy, SlideBrief
- DesignedSlide
- InspectionResult

## Известные проблемы (АКТУАЛЬНЫЕ)

### Критичные
- **Промпт Дизайнера слишком длинный** — layout_code.md + design_code_style1.md = ~12KB, бесплатная модель обрезает SVG. Решения: сжать документы, перейти на платную модель, или разделить на 2 вызова
- **google.generativeai deprecated** — нужен переход на google.genai
- **Качество дизайна нестабильно** — AI не соблюдает сетку, текст выходит за границы, выравнивание кривое
- **SVG text не переносится** — SVG не умеет word-wrap, текст выходит за карточки
- **time.sleep(3) между API-вызовами** — из-за лимитов бесплатной модели, прогон ~8 минут

### Стратегия улучшения дизайна (обсуждено)
- **Подход А (выбран): Постпроцессор-сетка** — AI генерирует SVG свободно, Python выравнивает по сетке. snap_to_grid, одинаковые ширины карточек, clamp в рабочую область
- Подход Б (отвергнут): JSON-скелеты с координатами — слишком негибкий
- **Few-shot эталоны** — для типовых слайдов (титул, разделитель), но не для всех
- **design_code_style1.md с точными числами** — уже подключен к Дизайнеру
- **R&D (после MVP):** Самообучающаяся система из примеров в интернете

### Постпроцессор PPTX (postprocess/pptx_fix.py)
- Скругляет только Rectangle (по имени shape), не трогает TextBox
- Убирает скругления у TextBox (SVG Engine иногда ставит roundRect)
- Задаёт INNER_MARGIN = Pt(0) для всех текстовых полей
- Устанавливает шрифт Google Sans
- Логика скруглений пока "тупая" — скругляет ВСЕ Rectangle, нужна умная фильтрация

## Map Redesign Pipeline (детали)
(без изменений — см. предыдущую версию CLAUDE.md)

### 7 модулей (в reverse/)
1. map_pipeline.py — оркестратор (шаги 4-5 — заглушки)
2. map_classifier.py — Gemini → тип 1-13 ✅
3. map_layer_splitter.py — PPTX → фон + объекты ✅
4. map_background.py — замена подложки через Mapbox + edge matching ✅
5. map_objects_redesign.py — пересадка через rel_x/rel_y ✅
6. map_vectorizer.py — R&D, отложен
7. map_assembler.py — финальная сборка PPTX ✅

## Что НЕ работает (проверено, НЕ повторять)
- vtracer, pypotrace, EasyOCR, keras-ocr на Windows — не ставятся
- pip install trace-skeleton — нужен Visual Studio Build Tools
- Векторизация маршрутов с пересечениями — всё провалилось (отложено в R&D)
- ORB/SIFT/matchTemplate между картами разных стилей — 0 совпадений (только Edge Matching)
- Nominatim БЕЗ viewbox — точки улетают в другие регионы
- Gemini геолокация спутника без текста — 0%

## Что ТОЧНО работает (проверено)
- Edge matching для совмещения карт
- Стиль streets-v12 для matching, light-v11 для финала
- Пересчёт пикселей → GPS → Mapbox @2x
- Кэширование geo_cache
- Полный пайплайн: PPTX → parse → JPG → classify → brain → design → SVG Engine → PPTX

## Ограничения API
- Gemini бесплатный: 5 RPM, 20 RPD (2.5 Flash), лимит на выходные токены
- Mapbox: 50k/мес бесплатно
- Nominatim: 1 req/sec, User-Agent обязателен

## Финансы
- Себестоимость редизайна (10 сл.): ~$0.85
- Себестоимость генерации (10 сл.): ~$0.50
- Цена клиенту: $3-10
- Маржа: 70-85%

## Эталонные тестовые файлы
- SmartGas.pptx (7 сл, оранжевый)
- Welcome.pptx (18 сл, синий)
- AI UDP.pptx (9 сл, синий)
- projects/test_map/test_maps.pptx (3 сл, для тестов карт)