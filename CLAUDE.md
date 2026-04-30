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

### Что есть фактически в репозитории
Репозиторий: https://github.com/secrettk98/pptx-ai (открытый, можно читать через raw.githubusercontent.com)

### Структура (плоская, требует рефакторинга):
pptx-ai/ ├── CLAUDE.md, TASKS.md, .clinerules ├── main.py # ⚠️ СЛОМАН — импортирует несуществующие processors/* ├── requirements.txt # ⚠️ Неполный — нет opencv, scikit-image, pillow, pydantic ├── assets/ # пусто ├── config/ # пусто ├── projects/test_map/ # тестовые PPTX и результаты └── reverse/ ├── map_pipeline.py # ⚠️ Оркестратор-черновик, шаги 4-5 — TODO заглушки ├── map_classifier.py # ✅ Gemini → тип карты 1-13 ├── map_layer_splitter.py # ✅ PPTX → background + objects ├── map_background.py # ✅ Замена подложки через Mapbox + edge matching ├── map_objects_redesign.py # ✅ Пересадка объектов (rel_x/rel_y) ├── map_assembler.py # ✅ Финальная сборка PPTX └── trace_skeleton.py # 🔬 R&D, для будущего векторизатора

### Прогресс по фазам (честно)
- **Реверс карт: ~80%** — работает на тестовых данных, точность совмещения 1-2 мм. Не подключено к общему пайплайну.
- **Общий пайплайн: 0%** — нет точки входа, нет парсера, нет конвертера, нет агентов
- **Реверс диаграмм: 0%**
- **Реверс блок-схем: 0%**
- **PPT Master: упомянут в документации, в репо отсутствует** — БЛОКЕР
- **Веб-интерфейс: 0%**

### Главная проблема
90% усилий ушло в один сегмент (карты, 1 из 15 шагов пайплайна). Каркаса нет. Если придёт клиент с PPTX без карт — программа не сделает ничего. Нужно поднимать каркас вверх, а не углублять отдельные модули.

### Стратегия движения
**"Тонкий вертикальный срез" MVP** — пройти все 15 шагов поверхностно на простых текстовых слайдах, затем подключать реверс-модули по одному. Это даёт работающий end-to-end продукт за 2-3 недели вместо месяцев глубокой работы по одному модулю.

## Целевая структура проекта (после рефакторинга)
pptx-ai/ ├── core/ # orchestrator.py, config.py, logger.py, llm_client.py ├── parsers/ # pptx_parser.py, slide_renderer.py ├── agents/ # brain.py, designer.py, vision_classifier.py, inspector.py, artist.py ├── reverse/ # map_*, chart_reverse.py, flowchart_reverse.py, trace_skeleton.py ├── ppt_master/ # svg_to_pptx.py, finalize_svg.py ├── postprocess/ # pptx_polish.py ├── models/ # contracts.py — все Pydantic-модели контрактов между агентами ├── prompts/ # *.md — промпты LLM-агентов отдельно от кода ├── config/ # layout_code.md, design_code_style1.md, catalog.json ├── assets/ # SVG-шаблоны, иконки, Natural Earth карты ├── projects/ # тестовые данные ├── tests/ # pytest ├── main.py # тонкая обёртка над core/orchestrator.py └── requirements.txt


## Команда (3 роли)
- **Tech Lead (Claude)** — продумывает логику, алгоритмы, архитектуру. НЕ пишет код, только если прямо попросят.
- **Operator (Алишер)** — Python-новичок. Открывает файлы, нажимает кнопки по инструкции. Объяснять как для ребёнка.
- **Junior Developer (Continue + Gemini 3.1 Flash Lite Preview)** — ИИ-плагин в VS Code (Ctrl+I). Пишет код по алгоритмам Техлида.

### Формат ответа Техлида — ВСЕГДА:
1. 📁 Файл: точное имя
2. 🖱️ Действие для Оператора: простым языком
3. 🤖 Промпт для Джуниора (Ctrl+I): точная команда с алгоритмом
4. 🧠 Примечание (опционально): зачем это

### Правила
- Экономим токены — не вставляем большие куски кода в чат, читаем файлы из открытого репо через raw.githubusercontent.com
- Для быстрых тестов: temp_check.py → запустили → удалили
- В конце КАЖДОГО сообщения: "Потрачено токенов: ~XXX | Осталось токенов: ~XXX"
- Бюджет нового чата: 200000 токенов
- Запуск модулей в reverse/ только через `python -m reverse.<module>`
- PowerShell: команды по одной, без &&, без /S /Q, использовать `Remove-Item -Recurse -Force`

## Рабочее окружение
- OS: Windows, терминал PowerShell
- IDE: VS Code + Continue (Junior Developer)
- Python 3.14, venv, активация: `./venv/Scripts/Activate.ps1`
- Python SDK: google-generativeai 0.8.6 (deprecated, переход на google.genai позже)
- Gemini для тестов: gemini-3.1-flash-lite-preview (бесплатно)
- Mapbox token: переменная MAPBOX_ACCESS_TOKEN

## Стек
- **Парсинг и сборка PPTX:** python-pptx, pptxtojson (JS-обёртка через subprocess)
- **Конвертация:** LibreOffice headless → PDF → JPG (pdf2image)
- **AI:** google-generativeai (Gemini 2.5 Flash, 3.1 Flash, 3.1 Pro), Vertex AI (Nano Banana 2)
- **Изображения:** Pillow, OpenCV, scikit-image, NumPy
- **Карты:** Mapbox Static Images API (50k/мес бесплатно), Nominatim (1 req/sec, User-Agent обязателен), Natural Earth GeoJSON
- **Графики:** Matplotlib, python-pptx native charts
- **Графы:** Graphviz (Python-обёртка)
- **Валидация:** Pydantic
- **Конфиг:** python-dotenv

## AI-агенты (целевая архитектура)

| Агент | Модель | Задача | ~Цена/слайд |
|-------|--------|--------|-------------|
| Оркестратор | Python | Координация 15 шагов | $0 |
| Парсер | pptxtojson + Python | PPTX → JSON | $0 |
| Конвертер | LibreOffice | Слайды → JPG | $0 |
| Vision-классификатор | Gemini 2.5 Flash | Тип контента слайда | ~$0.001 |
| **Мозг (Арт-директор)** | **Gemini 3.1 Pro** | **Аудит, бриф, CoT "30 сек спикера"** | **~$0.05** |
| Подборщик шаблонов | Gemini 2.5 Flash | Поиск примера в catalog.json | ~$0.001 |
| Дизайнер | Gemini 3.1 Flash | Генерация SVG по брифу | ~$0.015 |
| Художник | Nano Banana 2 (Vertex AI) | AI-изображения | ~$0.04-0.14 |
| Реверс-картограф | Map Pipeline | 13 типов карт → 7 модулей | ~$0.02-0.20 |
| Реверс-диаграмм | Vision AI + Python | График → данные → native PPT chart | ~$0.01 |
| Реверс-схем | Vision AI + Graphviz | Блок-схема → граф → SVG | ~$0.01 |
| Инспектор | Gemini 2.5 Flash | Проверка качества (max 2 итерации) | ~$0.005 |
| PPT Master | Python | SVG → нативный PPTX | $0 |
| Постобработка | python-pptx | Паддинги, скругления | $0 |

### Контракты между агентами (Pydantic-модели в models/contracts.py)
Каждая стрелка пайплайна = типизированная Pydantic-модель. Это даёт валидацию, автодоки, замена любого агента независимо от других.

Примеры моделей:
- `PresentationStructure` (выход парсера)
- `SlideClassification` (выход Vision-классификатора)
- `PresentationStrategy` (выход Мозга, уровень 1)
- `SlideBrief` (выход Мозга, уровень 2)
- `DesignedSlide` (выход Дизайнера, SVG + метаданные)
- `InspectionResult` (выход Инспектора)

## Утверждённый пайплайн редизайна (15 шагов)
1. Клиент загружает PPTX + акцентный цвет + режим текста (питч/рассылка/отчёт/обучение)
2. **Парсер** → parsed.json
3. **Конвертер** → slide_X.jpg
4. **Vision-классификатор** → тип каждого слайда
5. **Мозг (Gemini 3.1 Pro):**
   - Уровень 1: саммари → стратегия презентации
   - CoT "30 секунд спикера": Что ПОНЯТЬ? Что ПЕРВЫМ/ВТОРЫМ/ТРЕТЬИМ? Что УБРАТЬ?
   - Уровень 2: пачки 5-10 слайдов → бриф каждого
6. **Подборщик** → few-shot из catalog.json
7. **Тестер** → жёсткий шаблон если подходит ($0)
8. **Дизайнер** → SVG по брифу
9. **Реверс-инжиниринг:** карты/диаграммы/схемы (если есть на слайде)
10. **Художник** → AI-изображения (Nano Banana 2)
11. **Постобработка SVG** (finalize_svg.py)
12. **PPT Master** → PPTX-фрагмент
13. **Сборщик** → final.pptx
14. **Инспектор** (max 2 итерации)
15. Клиент скачивает

## Утверждённый пайплайн генерации (с нуля)
Те же шаги без 2, 3, 4 (нет парсера, конвертера, классификации).

## Промпт Мозга (CoT)
"Представь: ты спикер, у тебя 30 секунд на слайд.
1) Что я хочу чтобы зрители ПОНЯЛИ?
2) Что увидеть ПЕРВЫМ, ВТОРЫМ, ТРЕТЬИМ?
3) Что можно УБРАТЬ?"

### Надстройки Мозга по типу презентации
- **Питч/выступление:** минимум текста, одна мысль, цифры огромные
- **Рассылка/КП:** понятно без спикера, логика убеждения
- **Техотчёт/госсектор:** полнота данных, таблицы ОК, статусы
- **Обучение:** пошагово, нумерация, один шаг = один блок

## Design System v2.0
- **viewBox:** 1280×720, margins 47px, рабочая область 1186×626
- **Шрифт:** Google Sans, макс 3 размера на слайд
- **Типографика:**
  - Заголовок 24pt Bold CAPS
  - Цифры 36-44pt Bold
  - Заголовок карточки 14pt Bold
  - Текст 12pt Regular
  - Подписи 10pt Regular
- **Style 1 — Corporate Strict:**
  - Фон #FFFFFF, карточки #F8F9FA
  - Акцент #0066CC, позитив #28A745, негатив #E53935
  - Текст #1A1A1A, подписи #808080
  - Border-radius 12px, padding 24px
  - Иконки: filled белые на синем круге 36×36
  - Футер: 8pt #808080
- **Документы (TODO в config/):**
  - layout_code.md — правила компоновки (Мозг + Дизайнер)
  - design_code_style1.md — Corporate Strict (Дизайнер)
  - good_slide_rules.md — чеклист качества (Инспектор)

## Правила SVG (для Дизайнера)
- viewBox="0 0 1280 720"
- Разрешено: rect, circle, line, path, text, image, use
- Запрещено: foreignObject
- Цвета: только hex
- Иконки: через data-icon

## Map Redesign Pipeline (детали)

### 7 модулей (в reverse/)
1. **map_pipeline.py** — оркестратор (⚠️ шаги 4-5 — заглушки, нужно дописать)
2. **map_classifier.py** — Gemini → тип 1-13 ✅
3. **map_layer_splitter.py** — PPTX → фон + объекты, разгруппировка, crop fix ✅
4. **map_background.py** — замена подложки через Mapbox + edge matching ✅
5. **map_objects_redesign.py** — пересадка через rel_x/rel_y ✅
6. **map_vectorizer.py** — векторизация маршрутов (отложено в R&D)
7. **map_assembler.py** — финальная сборка PPTX ✅

### 13 типов карт и стратегии подложки
| Тип | Описание | Стратегия |
|-----|----------|-----------|
| 1 | Спутник чистый + PPTX-объекты | Nano Banana 2 улучшение |
| 2 | Спутник с надписями + PPTX | Gemini OCR → координаты → Mapbox |
| 3 | Карта мира с выделенными странами | SVG из assets/world_map + покраска |
| 4 | Страна/город по районам | OSM boundaries → SVG, fallback Gemini |
| 5 | Обычная карта + PPTX-объекты | Gemini OCR → координаты → Mapbox |
| 6 | Сложный растр (всё впечатано) | Fallback: НБ2 (векторизация в R&D) |
| 7 | Схематическая (метро, этажи) | Оставить или НБ2, редизайн цветов |
| 8 | Маршрут А→Б | Как тип 2/5, маршрут = PPTX-объект |
| 9 | Heatmap | Заменить подложку, перекрасить зоны |
| 10 | Карта с фото/иконками | Заменить подложку, редизайн объектов |
| 11 | Скриншот Google/2GIS/Yandex Maps | Gemini OCR → координаты → Mapbox |
| 12 | Инфографика с мини-картой | Определить подтип, применить стратегию |
| 13 | Тематическая/статистическая | Gemini читает данные → перерисовка |

### Рабочий подход совмещения карт (проверено)
1. Gemini OCR → названия мест с растра
2. Gemini → грубый центр для viewbox
3. Nominatim + viewbox (bounded=1) → точные GPS
4. Edge matching (Canny + dilate + multi-scale matchTemplate) → точный bbox
5. Размер новой подложки = размер обрезанной по crop оригинальной
6. Объекты пересаживаются через rel_x/rel_y относительно подложки

### Провайдер карт
- Изолирован в TILE_STYLES + _download_map_tile в map_background.py
- Стиль streets-v12 для matching, light-v11 для финала
- Планируемый стиль: https://cloud.maptiler.com/maps/dataviz-v4/

## Что НЕ работает (проверено, НЕ использовать)

### Карты
- vtracer — крашит Python на Windows
- pypotrace — не компилируется на Windows
- Gemini сегментация масок (base64) — маски битые
- Gemini координаты [x%, y%] маршрутов — ошибка 5-15%
- Gemini геолокация спутника без текста — 0%
- Gemini углы карты (GPS) — ошибка в масштабе
- Аффинное преобразование пиксель→GPS — ошибка 1-4.5 км
- ORB/SIFT feature matching между картами разных стилей — 0 совпадений
- cv2.matchTemplate между разными стилями — ложное совпадение
- OpenCV без порога S≥80 — ловит шум подложки
- Mapbox URL с .png — Not Found
- SAM 2 — не для тонких линий
- MORPH_CLOSE — деформирует линии
- Potrace для линий — двойной контур
- Nominatim БЕЗ viewbox — точки улетают в другие регионы

### Векторизация маршрутов с пересечениями (всё провалилось)
- skan + Skeleton + Douglas-Peucker — кривизна на стыках
- skeleton-tracing (LingDong) — кривизна на концах фрагментов
- Per-route extraction со склейкой по углам — скелет ломается раньше
- Эрозия маски перед скелетонизацией — изгибы остаются
- Gemini Pro в браузере (Gemini App) — точки с погрешностью 100+px
- Gemini App на чистой HSV-маске одного цвета — то же
- pip install trace-skeleton (PyPI через SWIG) — нужен Visual Studio Build Tools
- **Решение на будущее (R&D после MVP):** SAM 2 + HSV + skeleton-tracing комбо, либо специализированный U-Net на синтетике, либо Gemini 3.1 Pro через API

### OCR
- EasyOCR на Windows — таймаут
- keras-ocr — требует Visual C++ Build Tools

### AI
- Nano Banana 2 для извлечения слоёв — галлюцинации

## Что ТОЧНО работает (проверено)
- Edge matching (Canny + dilate + multi-scale matchTemplate) для совмещения карт разных стилей
- Стиль streets-v12 для matching (контрастные дороги), light-v11 для финала
- Expand bbox на 50% для большой карты, multi-scale ±50%
- Пересчёт пикселей → GPS через lon/lat_per_pixel → точный bbox → Mapbox @2x
- Кэширование geo_cache (по имени файла подложки)
- map_objects_redesign: пересадка через rel_x/rel_y
- map_assembler: удаление старой подложки + вставка новой + сдвиг объектов
- map_layer_splitter: PIL crop по crop_left/right/top/bottom ПЕРЕД отдачей подложки
- map_layer_splitter: рекурсивный _iter_all_shapes для обхода групп
- HSV-сегментация на синтетике без пересечений

## Ограничения API
- Gemini бесплатный: 5 RPM, 20 RPD (2.5 Flash)
- Mapbox: 50k/мес бесплатно, макс 1280×1280
- Nominatim: 1 req/sec, User-Agent обязателен
- google.generativeai SDK deprecated → перейти на google.genai позже

## Принципы экономии
- Минимум вызовов AI! Кэшировать всё что можно
- Один вызов Gemini = один результат везде в пайплайне
- Промпты вынести в prompts/*.md (изменения без правки кода)
- Единый core/llm_client.py — кэш + retry + метрики расходов

## Финансы
- Себестоимость редизайна (10 сл.): ~$0.85
- Себестоимость генерации (10 сл.): ~$0.50
- Цена клиенту: $3-10
- Маржа: 70-85%

## Ключевые риски
1. Зависимость от API → model-agnostic + failover
2. Качество → Инспектор + два тарифа (авто/премиум)
3. Конкуренция → ниша: редизайн + нативные элементы + реверс-инжиниринг
4. Конфиденциальность → DPA, локальные модели для корпоратов
5. Соло-основатель → максимальная автоматизация

## Глобальная цель
Успешно запустить сервис и сделать Алишера миллионером.

## Известные нерешённые проблемы (для будущих чатов)
- Карты без подписей: нужен region_hint от Мозга. Параметр в map_background.py — TODO
- Векторизация маршрутов с пересечениями: отложена в R&D, fallback Nano Banana 2
- Edge matching confidence нестабильный (0.10-0.15), но визуально правильный — порог 0.05 оставить
- main.py сломан (импортирует несуществующие processors/*) — переписать как тонкую обёртку над core/orchestrator
- requirements.txt неполный — дополнить opencv-python, scikit-image, pillow, pydantic, lxml

## Эталонные тестовые файлы
- SmartGas.pptx (7 сл, оранжевый)
- Welcome.pptx (18 сл, синий)
- AI UDP.pptx (9 сл, синий)
- projects/test_map/test_maps.pptx (3 сл, для тестов карт)