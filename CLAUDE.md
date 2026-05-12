# PPTX-AI — Project Context

## Продукт
B2B AI-сервис редизайна и генерации презентаций PowerPoint. PPTX + акцент → AI → нативный редактируемый PPTX.

## Принцип
LLM — мозг (стратегия, layout-план). Python — руки (парсинг, геометрия, SVG-рендер, сборка). Только нативные элементы PowerPoint, никаких PNG/PDF.

## Архитектура v4 (МАЙ 2026)

1. **Parser [Python]** → ParsedPresentation
2. **Strategy Director [AI flash]** → PresentationStrategy (1 вызов на всю презу)
3. **Architect [AI flash]** → LayoutPlan (поштучно с vision / батч без vision)
4. **LayoutEngine [Python]** → SlideGeometry (точные пиксели) — TODO
5. **SVG Renderer [Python]** → SVG код — TODO
6. **Reverse block** → Map / Chart / Scheme / Image — TODO
7. **Валидатор [Python]** → программная проверка — TODO
8. **Inspector [AI]** → визуальная проверка → цикл — TODO
9. SVG Engine → PPTX → Постобработка → Клиент

## Что работает
- ✅ Parser (parse_pptx_rich)
- ✅ Strategy Director — единый стиль на всю презентацию
- ✅ Architect — классификация + layout plan в одном шаге (замена Classifier + Senior + Junior)
- ✅ Контракты v4: LayoutPlan с slide_role, BlockGeometry, SlideGeometry
- ✅ prompt_assembler — assemble_rules(strategy) вместо assemble_prompt(classification)
- ✅ SVG Engine, Постпроцессоры
- ✅ Реверс карт ~80% (не подключён)
- ✅ google.genai SDK + Vertex AI (project: powermagic, us-central1)
- ✅ Дизайн-система: 12-колоночная сетка, модульные промпты
- ✅ Мульти-изображения в call_llm (image_path: str | list)

## Что нужно сделать (следующий чат)
- ❌ core/layout_engine.py — LayoutPlan → SlideGeometry (Python геометрия)
- ❌ core/svg_renderer.py — SlideGeometry → SVG (Python шаблонизатор)
- ❌ core/orchestrator.py — переписать под новый пайплайн (Strategy → Architect → LayoutEngine → SVG Renderer)
- ❌ Тест на 1 слайде

## Окружение
- Windows, PowerShell, VS Code + Continue, Python 3.14
- SDK: google-genai, Vertex AI ($300 credits)
- Модели: gemini-2.5-flash, gemini-2.5-pro
- LibreOffice 26.2, Poppler 25.12, gcloud CLI

## Модели (config.py)
- MODEL_CLASSIFIER: gemini-2.5-flash (Architect + Strategy Director)
- MODEL_BRAIN: gemini-2.5-pro (зарезервировано для сложных задач)
- MODEL_DESIGNER: gemini-2.5-pro (зарезервировано)
- MODEL_VISION: gemini-2.5-flash (зарезервировано)
- MODEL_INSPECTOR: gemini-2.5-flash
- MODEL_CHEAP: gemini-2.5-flash-lite

## Команда
- **Tech Lead (Claude)** — логика, архитектура, код целиком
- **Operator (Алишер)** — открывает файлы, копирует код, нажимает кнопки

## Формат ответа Техлида
1. 📁 Файл: точное имя
2. 🖱️ Действие для Оператора
3. 💾 Готовый код целиком
4. 🧠 Примечание (опционально)

## Правила
- Экономим токены и деньги
- Тесты только на 1 слайде (--slides=0), потом расширяем
- Перед правкой большого файла — Techlead обязан прочитать его актуальную версию
- PowerShell: команды по одной
- Никаких изменений в файлах, которые Techlead не читал
- GitHub: https://github.com/secrettk98/pptx-ai

## Ключевые файлы
- **core/orchestrator.py** — главный пайплайн (НУЖНО ПЕРЕПИСАТЬ)
- **core/llm_client.py** — вызовы API (sync + async, system_instruction, мульти-изображения)
- **core/prompt_assembler.py** — assemble_rules(strategy) из config/ модулей
- **core/llm_normalize.py** — нормализация ответов AI под Pydantic
- **core/ollama_client.py** — оставлен на будущее
- **agents/strategy_director.py** — единая стратегия на всю презентацию
- **agents/architect.py** — классификация + layout plan (замена classifier + senior + junior)
- **models/contracts.py** — Pydantic модели v4
- **parsers/pptx_parser.py** — parse_pptx_rich
- **parsers/slide_renderer.py** — PPTX → JPG через LibreOffice
- **config/** — правила дизайн-системы (.md модули)
- **prompts/** — промпты агентов (.md)
- **reverse/** — модули реверса (не подключены)

## Активные контракты (models/contracts.py)
GroupPosition, ShapeStyle, ParsedShape, ParsedSlide, ParsedPresentation,
PresentationStrategy,
ColumnInstruction, RowInstruction, FooterInstruction, LayoutPlan,
BlockGeometry, SlideGeometry,
DesignedSlide

## Решения принятые
- Architect = Classifier + Senior в одном шаге (flash вместо pro, экономия 10x)
- Junior Designer УДАЛЁН — заменяется Python LayoutEngine + SVG Renderer
- LLM считает только grid-колонки, Python считает пиксели
- Strategy Director — 1 вызов flash на всю презу (~$0.002)
- Architect: поштучно с vision / батч до 10 без vision
- Дизайн-система: 12 колонок, 6 типов объектов, модульные промпты
- header_type на уровне презентации (fixed/floating из Strategy)
- Кэш: temp/cache/ (strategy, layout_plan, svg)
- Orchestrator CLI: --no-cache, --no-vision, --no-batch, --slides=0,1,2, --accent=#XXXXXX