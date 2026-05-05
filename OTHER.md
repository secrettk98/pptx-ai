# PPTX-AI — Справочная информация

## Структура репозитория
pptx-ai/ ├── core/ # orchestrator.py, config.py, logger.py, llm_client.py ├── parsers/ # pptx_parser.py, slide_renderer.py ├── agents/ # brain.py, designer.py, vision_classifier.py ├── reverse/ # map_pipeline.py, map_classifier.py, map_layer_splitter.py, │ # map_background.py, map_objects_redesign.py, map_assembler.py ├── svg_engine/ # drawingml_.py, pptx_.py, convert.py (PPT Master, MIT) ├── postprocess/ # svg_fix.py, pptx_fix.py ├── models/ # contracts.py ├── prompts/ # designer.md, vision_classifier.md, brain_level1.md, brain_level2.md ├── config/ # layout_code.md, design_code_style1.md ├── assets/ # TODO ├── projects/ # тестовые данные ├── tests/ # TODO ├── main.py ├── requirements.txt ├── CLAUDE.md, TASKS.md, OTHER.md


## Стек
python-pptx, LibreOffice headless, pdf2image + Poppler, google-genai (Vertex AI), svg_engine (PPT Master, MIT), Pillow, OpenCV, scikit-image, NumPy, Mapbox, Nominatim, Pydantic, python-dotenv

## Ценообразование Vertex AI
- gemini-2.5-flash: вход $0.30/1M, выход $2.50/1M (~$0.04 за 3 слайда)
- gemini-2.5-pro: вход $1.25/1M, выход $10.00/1M (~$0.70 за 10 слайдов)
- gemini-2.5-flash-lite: вход $0.10/1M, выход $0.40/1M

## Финансы
- Себестоимость редизайна (10 сл.): ~$0.85
- Себестоимость генерации (10 сл.): ~$0.50
- Цена клиенту: $3-10, маржа 70-85%

## Map Pipeline (7 модулей)
1. map_pipeline.py — оркестратор
2. map_classifier.py — Gemini → тип 1-13
3. map_layer_splitter.py — PPTX → фон + объекты
4. map_background.py — Mapbox + edge matching
5. map_objects_redesign.py — пересадка через rel_x/rel_y
6. map_vectorizer.py — R&D, отложен
7. map_assembler.py — финальная сборка

## Контракты (models/contracts.py)
PresentationStructure, SlideInfo, SlideClassification, PresentationStrategy, SlideBrief, DesignedSlide, InspectionResult

## Ограничения API
- Vertex AI: $300 trial credits
- Mapbox: 50k/мес бесплатно
- Nominatim: 1 req/sec, User-Agent обязателен

## Эталонные тестовые файлы
- SmartGas.pptx (7 сл, оранжевый)
- Welcome.pptx (18 сл, синий)
- AI UDP.pptx (9 сл, синий)
- projects/test_map/test_maps.pptx (3 сл)

## Что НЕ работает (НЕ повторять)
- vtracer, pypotrace, EasyOCR, keras-ocr на Windows
- pip install trace-skeleton — нужен Visual Studio Build Tools
- Векторизация маршрутов с пересечениями — отложено в R&D
- ORB/SIFT/matchTemplate между картами разных стилей — только Edge Matching
- Nominatim БЕЗ viewbox — точки улетают
- gemini-3.1-flash-lite-preview через Vertex AI — 404
- Подход Б для сетки (JSON-скелеты) — отвергнут

## Что ТОЧНО работает
- Edge matching для совмещения карт
- Mapbox streets-v12 для matching, light-v11 для финала
- Пересчёт пикселей → GPS → Mapbox @2x
- Кэширование geo_cache
- Кодировка SVG — UTF-8, кириллица корректна (кракозябры только в терминале)

## Фазы 7-8 (после MVP)
- Фаза 7: FastAPI бэкенд, фронтенд, оплата, деплой
- Фаза 8: векторизация маршрутов, самообучение шаблонов, API иконок, локальные модели