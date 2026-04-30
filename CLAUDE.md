# PPTX-AI — Project Context

## Рабочее окружение
- GitHub: https://github.com/secrettk98/pptx-ai (приватный)
- OS: Windows
- Терминал: PowerShell (команды ТОЛЬКО по одной, НЕ через &&, НЕ через /S /Q, использовать Remove-Item -Recurse -Force)
- IDE: VS Code + Continue (Gemini 3.1 Flash Lite Preview как Junior Developer)
- Python 3.14, venv
- Python SDK: google-generativeai 0.8.6 (deprecated но рабочий, переход на google.genai позже)
- Gemini модель в коде: gemini-3.1-flash-lite-preview (бесплатная, для тестов)
- Mapbox token переменная: MAPBOX_ACCESS_TOKEN

## Формат работы (команда из 3 ролей)

### Роли:
- Tech Lead (Claude): Продумывает логику, алгоритмы, архитектуру. НЕ пишет код, только если прямо попросят.
- Operator (Алишер): Уровень Python = ноль. Открывает файлы, нажимает кнопки по инструкции. Объяснять как для ребёнка.
- Junior Developer (Continue, Gemini 3.1 Flash Lite Preview): ИИ-плагин в VS Code (Ctrl+I). Пишет код по алгоритмам от Техлида.

### Формат ответа Техлида — ВСЕГДА по шаблону:
1. 📁 Файл: [точное название файла]
2. 🖱️ Действие для Оператора: [простым языком, для новичка]
3. 🤖 Промпт для Джуниора (Ctrl+I в VS Code): [точная команда с алгоритмом]
4. 🧠 Примечание от Техлида (опционально): [зачем мы это делаем]

### Правила:
- Экономим токены — не вставляем большие куски кода в чат
- Для быстрых тестов: пишем temp_check.py, запускаем, удаляем
- В конце КАЖДОГО сообщения: "Потрачено токенов: ~XXX | Осталось токенов: ~XXX"
- Начальный бюджет нового чата: 200000 токенов
- Запуск модулей в reverse/ только через python -m reverse.<module> (пакетная структура)
- Глобальная цель: успешно запустить сервис и сделать Алишера миллионером

## Суть продукта
B2B AI-сервис редизайна презентаций PowerPoint.
Клиент загружает .pptx + акцентный цвет → AI анализирует → генерирует SVG → PPT Master собирает нативный редактируемый .pptx.
Второй режим: генерация презентации с нуля из текста/документов.

## Главный принцип
LLM — мозг (анализирует, выбирает layout, составляет бриф).
Python — руки (парсит, постобрабатывает, собирает PPTX).
Никаких PNG/PDF — только редактируемые нативные элементы PowerPoint.

## Киллер-фича
Реверс-инжиниринг сложных элементов:
- Блок-схемы → Vision AI → граф → Graphviz → SVG → PPTX
- Диаграммы → Vision AI → данные → Matplotlib/python-pptx → нативный график
- Карты → Map Redesign Pipeline v2.1 (13 типов, 7 модулей) → PPTX

## Стек
- python-pptx, pydantic, Pillow, dotenv
- PPT Master (svg_to_pptx.py, finalize_svg.py) — SVG → PPTX
- Graphviz, Matplotlib — отрисовка схем и графиков
- OpenCV + NumPy + scikit-image + skan — HSV-сегментация, скелетонизация
- trace_skeleton (LingDong, Pure Python в reverse/trace_skeleton.py) — векторизация скелетов (для R&D)
- Mapbox Static Images API (50k бесплатно/мес, макс 1280x1280, URL без .png)
- OpenStreetMap Nominatim (бесплатно, 1 req/sec, User-Agent обязателен)
- Natural Earth GeoJSON — SVG карты мира/стран (public domain)
- Nano Banana 2 через Vertex AI ($300 кредитов)
- Парсер входящей PPTX: pptxtojson (JS)

## Структура проекта (актуальная)
pptx-ai/
├── ppt-master/              # PPT Master (SVG → PPTX)
├── projects/
│   └── test_map/            # Тестовые данные карт
│       ├── test_maps.pptx              # Тестовый PPTX (3 слайда)
│       ├── test_maps_grouped.pptx      # Тест разгруппировки (1 слайд со сгруппированной картой)
│       ├── slide3_map.png              # Скриншот слайда 3 для R&D векторизатора
│       ├── layers/                     # Извлечённые подложки
│       └── output/                     # Результаты тестов
├── config/
│   ├── layout_code.md       # Правила компоновки
│   └── design_code_style1.md # Corporate Strict стиль
├── reverse/                 # Реверс-инжиниринг карт
│   ├── __init__.py
│   ├── map_pipeline.py             # ✅ Оркестратор
│   ├── map_classifier.py           # ✅ Gemini → тип карты 1-13
│   ├── map_layer_splitter.py       # ✅ PPTX → background + objects (с crop fix + разгруппировкой)
│   ├── map_background.py           # ✅ Замена подложки (mapbox)
│   ├── map_objects_redesign.py     # ✅ Пересадка объектов (rel_x/rel_y)
│   ├── map_assembler.py            # ✅ Финальная сборка (без дублирующего crop)
│   ├── trace_skeleton.py           # 🔬 LingDong's skeleton tracer (R&D, для будущего векторизатора)
│   └── map_vectorizer.py           # ❌ Отложено в R&D (см. TASKS.md)
├── assets/                  # SVG карты (TODO)
├── main.py
├── requirements.txt
├── CLAUDE.md
├── TASKS.md
└── .env

## AI-агенты и модели
| Агент | Модель | Задача | ~Цена/слайд |
|-------|--------|--------|-------------|
| Оркестратор | Python | Координирует пайплайн | $0 |
| Парсер | pptxtojson (JS) | PPTX → JSON | $0 |
| Конвертер | LibreOffice | Слайды → JPG | $0 |
| Vision-классификатор | Gemini 2.5 Flash | Классификация изображений | ~$0.001 |
| Центральный мозг | Gemini 3.1 Pro | Арт-директор: аудит, бриф, CoT | ~$0.05 |
| Подборщик шаблонов | Gemini 2.5 Flash | Поиск примера в catalog.json | ~$0.001 |
| Дизайнер-верстальщик | Gemini 3.1 Flash | Генерация SVG по брифу | ~$0.015 |
| Художник | Nano Banana 2 (Vertex AI) | AI-изображения + улучшение спутника | ~$0.04-0.14 |
| Инспектор | Gemini 2.5 Flash | Проверка качества | ~$0.005 |
| PPT Master | Python | SVG → PPTX | $0 |
| Постобработка | Python (python-pptx) | Паддинги, скругления | $0 |
| Реверс-инжиниринг | Vision AI + Python | Схемы→Graphviz, графики→Matplotlib | ~$0.01 |
| Картограф | Map Pipeline v2.1 | 13 типов карт → 7 модулей | ~$0.02-0.20 |

### Model routing:
- Дорогая логика (Gemini 3.1 Pro) → Мозг
- Быстрая генерация (Gemini 3.1 Flash) → Дизайнер
- Дешёвая классификация (Gemini 2.5 Flash) → Vision, Подборщик, Инспектор
- Тесты (gemini-3.1-flash-lite-preview) → текущая разработка

## Map Redesign Pipeline v2.1

### 7 модулей:
1. map_pipeline.py — оркестратор
2. map_classifier.py — Gemini → тип 1-13
3. map_layer_splitter.py — PPTX парсинг → фон + объекты
4. map_background.py — замена подложки
5. map_objects_redesign.py — пересадка объектов
6. map_vectorizer.py — векторизация маршрутов (R&D, отложено)
7. map_assembler.py — финальная сборка

### 13 типов карт и стратегии:
| Тип | Описание | Стратегия подложки |
|-----|----------|-------------------|
| 1 | Спутник чистый + PPTX-объекты | НБ2 улучшение |
| 2 | Спутник с надписями + PPTX-объекты | Gemini OCR → координаты → Mapbox |
| 3 | Карта мира с выделенными странами | SVG из assets/world_map + покраска |
| 4 | Страна/город по районам | OSM boundaries → SVG, fallback Gemini |
| 5 | Обычная карта + PPTX-объекты | Gemini OCR → координаты → Mapbox |
| 6 | Сложный растр (всё впечатано) | Fallback: НБ2 улучшение (векторизация в R&D) |
| 7 | Схематическая (метро, этажи) | Оставить/НБ2, редизайн цветов |
| 8 | Маршрут А→Б | Как тип 2/5, маршрут = PPTX-объект |
| 9 | Тепловая карта (heatmap) | Заменить подложку, перекрасить зоны |
| 10 | Карта с фото/иконками | Заменить подложку, редизайн объектов |
| 11 | Скриншот Google Maps/2GIS/Yandex | Gemini OCR → координаты → Mapbox |
| 12 | Инфографика с мини-картой | Определить подтип, применить стратегию |
| 13 | Тематическая/статистическая | Gemini читает данные → перерисовка |

### Рабочий подход совмещения карт (проверено):
1. Gemini OCR → названия мест с растра
2. Gemini → грубый центр для viewbox
3. Nominatim + viewbox (bounded=1) → точные GPS
4. Edge matching (Canny + dilate + multi-scale matchTemplate) → точный bbox
5. Размер новой подложки = размер обрезанной по crop оригинальной (НЕ хардкодить)
6. Объекты пересаживаются через rel_x/rel_y относительно подложки

## Что НЕ работает (проверено, НЕ использовать)
- vtracer — крашит Python на Windows
- pypotrace — не компилируется на Windows
- Gemini сегментация масок (base64) — маски битые
- Gemini координаты [x%, y%] маршрутов — ошибка 5-15%
- Gemini геолокация спутника без текста — 0%
- Gemini углы карты (GPS) — ошибка в масштабе
- Gemini crop (2 карты → обрезка) — неточно
- Аффинное преобразование пиксель→GPS — ошибка 1-4.5 км
- ORB/SIFT feature matching между картами разных стилей — 0 совпадений
- Template matching (cv2.matchTemplate) между стилями — ложное совпадение
- OpenCV без порога S≥80 — ловит шум подложки
- Mapbox URL с .png — Not Found
- Mapbox URL с дублированием access_token — ошибка
- SAM 2 — не для тонких линий (для R&D векторизатора попробовать SAM 2 + HSV комбо)
- MORPH_CLOSE — деформирует линии
- Potrace для линий — двойной контур
- EasyOCR на Windows — таймаут
- keras-ocr — требует Visual C++ Build Tools
- Nano Banana 2 для извлечения слоёв — галлюцинации
- Nominatim БЕЗ viewbox — точки улетают в другие регионы
- skan + Skeleton + Douglas-Peucker для маршрутов с пересечениями — кривизна на стыках
- skeleton-tracing (LingDong, trace_skeleton.py) для маршрутов с пересечениями — кривизна на концах фрагментов
- Per-route extraction (склейка фрагментов одного цвета по углам через занятость другим цветом) — не помогает, скелет ломается раньше склейки
- Эрозия маски перед скелетонизацией — изгибы остаются
- Gemini Pro в браузере (Gemini App) для извлечения polyline маршрутов — точки с погрешностью сотни px
- Gemini App на чистой HSV-маске одного цвета — не помогает, точки всё равно неточные
- pip install trace-skeleton (PyPI обёртка через SWIG) — требует Visual Studio Build Tools на Windows. Решение: использовать Pure Python версию (reverse/trace_skeleton.py)

## Design System v2.0
- layout_code.md → правила компоновки (для Мозга + Дизайнера)
- design_code_style1.md → Corporate Strict (для Дизайнера)
- good_slide_rules.md → чеклист качества (для Инспектора, TODO)
- Размеры: viewBox 1280×720, margins 47px, рабочая область 1186×626
- Шрифт: Google Sans, макс 3 размера на слайд

## Утверждённый пайплайн (редизайн) — 15 шагов
1. Клиент загружает PPTX + акцентный цвет + режим текста
2. Парсер (pptxtojson JS) → структура.json
3. Конвертер → slide_X.jpg
4. Vision-классификатор (Gemini 2.5 Flash)
5. Центральный мозг (Gemini 3.1 Pro):
   - Уровень 1: саммари → стратегия + тип презентации
   - "30 секунд спикера" (CoT): Что ПОНЯТЬ? Что ПЕРВЫМ/ВТОРЫМ/ТРЕТЬИМ? Что УБРАТЬ?
   - Надстройка: выступление/рассылка/техотчёт/обучение
   - Уровень 2: пачки 5-10 слайдов → бриф каждого
6. Подборщик → few-shot из catalog.json
7. Тестер → жёсткий шаблон если подходит ($0)
8. Дизайнер (Gemini 3.1 Flash) → SVG по брифу
9. Реверс-инжиниринг: схемы→Graphviz, графики→Matplotlib, карты→Map Pipeline
10. Художник (Nano Banana 2)
11. Постобработка SVG (finalize_svg.py)
12. PPT Master → PPTX
13. Постобработка PPTX (python-pptx)
14. Инспектор (Gemini 2.5 Flash, max 2 попытки)
15. Клиент скачивает

## Утверждённый пайплайн (генерация с нуля)
1. Клиент загружает текст/документ + акцентный цвет
2. Центральный мозг → анализ + стратегия + план
3-15. Те же шаги без парсера, конвертера и Vision

## Design System v2.0 — подробности

### Промпт Мозга (CoT):
"Представь: ты спикер, 30 секунд на слайд.
1) Что я хочу чтобы они ПОНЯЛИ?
2) Что увидеть ПЕРВЫМ, ВТОРЫМ, ТРЕТЬИМ?
3) Что можно УБРАТЬ?"

### Надстройки по типу:
- Выступление/питч: минимум текста, одна мысль, цифры огромные
- Рассылка/КП: понятно без спикера, логика убеждения
- Техотчёт/госсектор: полнота данных, таблицы ОК, статусы
- Обучение: пошагово, нумерация, один шаг = один блок

### Типографика:
Заголовок 24pt Bold CAPS | Цифры 36-44pt Bold | Заголовок карточки 14pt Bold
Текст 12pt Regular | Подписи 10pt Regular | Шрифт: Google Sans, макс 3 размера

### Style 1 — Corporate Strict:
Фон #FFFFFF | Карточки #F8F9FA | Акцент #0066CC | Позитив #28A745 | Негатив #E53935
Текст #1A1A1A | Подписи #808080 | Border-radius 12px | Padding 24px
Иконки: filled белые на синем круге 36×36 | Футер: 8pt #808080

## Финансы
- Себестоимость редизайна (10 сл.): ~$0.85
- Себестоимость генерации (10 сл.): ~$0.50
- Цена клиенту: $3-10
- Маржа: 70-85%

## Ключевые риски
1. Зависимость от API → model-agnostic + failover
2. Качество → инспектор + два тарифа (авто/премиум)
3. Конкуренция → ниша: редизайн + нативные элементы + реверс-инжиниринг
4. Конфиденциальность → DPA, локальные модели для корпоратов
5. Соло-основатель → максимальная автоматизация

## Nano Banana 2
- Бесплатно: Gemini App — 3 изображения/день, 1 МП
- Vertex AI: $300 кредитов на 90 дней, ~$0.04-0.14/изображение
- Gemini 2.5+ сегментация (JSON + base64 маска) — НЕ ТЕСТИРОВАНО, запланировано

## Правила SVG
- viewBox="0 0 1280 720"
- Только: rect, circle, line, path, text, image, use
- Нет foreignObject, hex-цвета, иконки через data-icon

## Ограничения API
- Gemini бесплатный: 5 RPM, 20 RPD (2.5 Flash)
- Mapbox: 50k/мес бесплатно, макс 1280x1280
- Nominatim: 1 req/sec, User-Agent обязателен
- google.generativeai SDK deprecated → перейти на google.genai позже

## Проверено и работает
- Edge matching (Canny + dilate + multi-scale matchTemplate) для совмещения карт разных стилей
- Стиль streets-v12 для matching (контрастные дороги), light-v11 для финала
- Expand bbox на 50% для большой карты, multi-scale ±50% от ожидаемого
- Пересчёт пикселей → GPS через lon/lat_per_pixel → точный bbox → Mapbox @2x
- Кэширование geo_cache (по имени файла подложки) — экономит Gemini + Nominatim
- map_objects_redesign: пересадка через относительные координаты (rel_x/rel_y)
- map_assembler: удаление старой подложки + вставка новой + сдвиг объектов
- map_layer_splitter: PIL crop по crop_left/right/top/bottom ПЕРЕД отдачей подложки
- map_layer_splitter: рекурсивный _iter_all_shapes для обхода групп
- HSV-сегментация на простых синтетических кейсах (без пересечений) — РАБОТАЕТ
- Минимум вызовов AI! Кэшировать всё что можно. Один вызов Gemini = один результат везде.

## Провайдер карт
- Изолирован в TILE_STYLES + _download_map_tile в map_background.py
- Для смены на MapTiler: добавить строку в TILE_STYLES, поменять final_style
- Планируемый стиль: https://cloud.maptiler.com/maps/dataviz-v4/

## Известные нерешённые проблемы (для следующих чатов)
- Карты без подписей: Gemini не может определить регион (0%). Нужен region_hint от Мозга. Параметр region_hint в map_background.py — TODO
- Векторизация маршрутов с пересечениями (тип 6): отложена в R&D. Все классические CV-подходы и Vision LLM не дали результата. См. подробности в TASKS.md. Текущий fallback — Nano Banana 2 улучшение растра.
- Edge matching confidence нестабильный (0.10-0.15), но результат визуально правильный. Порог 0.05 оставить.