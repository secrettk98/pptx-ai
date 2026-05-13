# PPTX-AI — Project Context

## Продукт
B2B AI-сервис редизайна презентаций PowerPoint. PPTX + акцент → AI → нативный редактируемый PPTX.

## Принцип
LLM — мозг (стратегия, layout-план). Python — руки (парсинг, flex-layout, точные метрики, SVG-рендер, сборка). Только нативные элементы PowerPoint.

## Архитектура v4 (МАЙ 2026)

1. **Parser** → ParsedPresentation
2. **Strategy Director [flash]** → PresentationStrategy (1 вызов)
3. **Architect [flash]** → LayoutPlan (сейчас 1 вызов; возможен возврат к 2-проходной системе)
4. **LayoutEngine v5 [stretchable + Pillow]** → SlideGeometry + RenderedText ✅
5. **SVG Renderer v5** → SVG (тупой, по координатам) ✅
6. **Reverse block** → Map / Chart / Scheme / Image — TODO
7. **Валидатор** — TODO
8. **Inspector [AI]** — TODO
9. SVG Engine → PPTX → Постобработка → Клиент

## Технологии
- **stretchable** — Python bindings для Taffy (Rust). Flex/grid layout.
  - `Style` frozen, все параметры в `Node(...)` сразу
  - `node.get_box(Edge.BORDER)` — координаты относительно родителя
  - Абсолютные координаты — суммой по дереву (`_abs_box`)
  - Запуск: `python -m core.layout_engine`
- **Pillow + Inter TTF** — точные метрики текста
  - `core/text_metrics.py`: measure / wrap / fit_height / measure_block / truncate / baseline_offset
  - Шрифты: `assets/fonts/Inter-Regular.ttf`, `Inter-Bold.ttf`

## Окружение
- Windows 11, PowerShell, VS Code, Python 3.14.4
- google-genai SDK, Vertex AI (powermagic, us-central1, $300 credits)
- gemini-2.5-flash (Architect, Strategy), gemini-2.5-pro (резерв)
- stretchable, Pillow 12.2, LibreOffice 26.2

## Команда
- **Tech Lead (Claude)** — логика, архитектура, код
- **Operator (Алишер)** — копирует код, запускает команды

## Формат ответа
1. 📁 Файл: точное имя
2. 🖱️ Действие для Оператора
3. 💾 Код точечно: "найди X, замени на Y" (не файл целиком)
4. 🧠 Примечание (опционально)

## Правила
- **НЕ ПИШИ КОД И НЕ НАЧИНАЙ ДЕЙСТВОВАТЬ БЕЗ СОГЛАСИЯ АЛИШЕРА** — сначала предложи план, дождись "делаем"
- Экономим токены и деньги
- Тесты на 1 слайде (--slides=0), тестовый файл: projects/test_map/test_maps.pptx (НЕ layout.pptx!)
- Перед правкой большого файла — прочитать актуальную версию
- PowerShell: команды по одной
- Точечные правки, кроме нового файла или полной переписи
- GitHub: https://github.com/secrettk98/pptx-ai
- Не латай дырки магическими числами — ищи корень проблемы
- Layout Engine — тупой исполнитель, все умные решения (что влезет, как трансформировать контент) — на стороне AI-мозга (Architect)

## Ключевые файлы
- **core/layout_engine.py** — v5 (stretchable + Pillow) ✅
- **core/svg_renderer.py** — v5 (тупой рендерер по RenderedText) ✅
- **core/text_metrics.py** — метрики Pillow + Inter ✅
- **core/orchestrator.py** — пайплайн v4
- **core/llm_client.py** — вызовы API
- **core/prompt_assembler.py** — сборка design rules из config/ модулей
- **agents/strategy_director.py** — стратегия презы
- **agents/architect.py** — classify + layout (1 вызов flash)
- **models/contracts.py** — Pydantic v4 + RenderedText
- **parsers/pptx_parser.py** — parse_pptx_rich

## Система инструкций (config/)
Модульная архитектура дизайн-правил, задокументирована в config/handoff.md.
- **config/handoff.md** — ЧИТАТЬ ПЕРВЫМ, полный контекст проекта и архитектуры правил
- **config/core_rules.md** — фундамент: 6 типов объектов, композиция, grid, правила
- **config/classifier.md** — промпт классификатора (сейчас НЕ подключён, встроен в Architect)
- **config/modules_map.md** — какие модули грузить по результату классификации (сейчас НЕ используется)
- **config/card.md** — правила карточек
- **config/patterns.md** — SVG паттерны (timeline, process, swot и т.д.)
- **config/headers/** — type_a_rigid.md, type_b_floating.md, type_c_top.md
- **config/styles/** — soft.md, strict.md
- **prompts/architect.md** — текущий промпт Architect (упрощённый, требует переработки)

### Проблема с текущей сборкой промпта
prompt_assembler.py грузит ВСЕ модули всегда (core_rules + style + header + card + patterns).
По задумке (modules_map.md) должен фильтровать по результату классификации.
Architect получает ~1000+ строк правил, тонет в них и выбирает лёгкий путь — копирует оригинал.

## Контракты (models/contracts.py)
GroupPosition, ShapeStyle, ParsedShape, ParsedSlide, ParsedPresentation,
PresentationStrategy,
ColumnInstruction, RowInstruction, FooterInstruction, LayoutPlan,
RenderedText, BlockGeometry (+rendered_texts), SlideGeometry,
DesignedSlide

## Принятые решения
- Architect = Classifier + Senior (1 flash вызов вместо 2 pro)
- Junior УДАЛЁН — Python LayoutEngine + SVG Renderer
- RenderedText в BlockGeometry — layout мерит 1 раз, SVG только рисует
- Ширина колонок через PCT (не flex_grow) — иначе intrinsic ломает grid
- flex_basis=0 + размер в % — настоящая 12-колоночная сетка
- wrapper_nodes в BlockCtx — координаты обёрток (card/cell) в RenderedText.extra
- baseline_offset через Pillow getmetrics() — универсальный baseline
- Линия heading = отдельный узел в layout (accent_line)
- Центрирование текста в ячейках — в layout_engine, не в рендерере

## Критическая проблема (Фаза 4.8.1)
При тестировании на реальной презентации выявлено:
1. Контент вылезает за границы слайда (overflow 100+ px)
2. Architect не трансформирует контент (копирует структуру оригинала)
3. Нет retry-механизма при overflow

Корень: Architect не понимает бюджет пространства и не мыслит креативно.
Layout Engine НЕ МОЖЕТ решить эту проблему — только AI-мозг.
Нужно: переработать промпт Architect + добавить retry в Orchestrator.
Подробности и варианты решения — в TASKS.md, фаза 4.8.1.