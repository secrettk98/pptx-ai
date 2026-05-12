# PPTX-AI — Project Context

## Продукт
B2B AI-сервис редизайна и генерации презентаций PowerPoint. PPTX + акцент → AI → нативный редактируемый PPTX.

## Принцип
LLM — мозг (стратегия, классификация, layout, бриф). Python — руки (парсинг, геометрия, сборка). Только нативные элементы PowerPoint, никаких PNG/PDF.

## Архитектура v3 (МАЙ 2026)

1. **Parser [Python]** → ParsedPresentation
2. **Strategy Director [AI]** → PresentationStrategy (1 вызов на всю презу)
3. **Classifier [AI]** → SlideClassificationV2 (батч до 20 / поштучно с vision)
4. **Senior Designer [AI]** → LayoutPlan (батч до 10)
5. **Junior Designer [AI]** → SVG (async, до 5 параллельно)
6. **Reverse block** → Map / Chart / Scheme / Image (TODO)
7. **Валидатор [Python]** → программная проверка (TODO)
8. **Inspector [AI]** → визуальная проверка → цикл (TODO)
9. SVG Engine → PPTX → Постобработка → Клиент

## Что работает
- ✅ Полный пайплайн: Parser → Strategy → Classifier → Senior → Junior → SVG
- ✅ Strategy Director — единый стиль на всю презентацию (header_type, style_mode, accent_color, presentation_mode, allow_rewrite)
- ✅ Orchestrator v3 с кэшем (включая strategy), батчами, async
- ✅ system_instruction во всех агентах
- ✅ SVG Engine, Постпроцессоры
- ✅ Реверс карт ~80% (не подключён)
- ✅ google.genai SDK + Vertex AI (project: powermagic, us-central1)
- ✅ Дизайн-система: 12-колоночная сетка, модульные промпты
- ✅ Поддержка мульти-изображений в call_llm (image_path: str | list)
- ✅ Чистка мёртвого кода: brain.py, designer.py, vision_classifier.py удалены, contracts.py отчищен

## Известные проблемы (приоритет!)
- ❌ Junior плохо центрирует контент вертикально — огромные пустоты внизу
- ❌ Senior иногда кладёт несколько карточек в одну колонку grid_span=12 вместо разделения 6+6
- ❌ Senior создаёт лишние text-ряды для коротких подзаголовков (должен быть subtitle)
- ❌ Junior получает LayoutPlan дважды (плейсхолдер `{layout_plan}` в системном промпте остаётся как литерал)
- ❌ Strategy.allow_rewrite пока никуда не передаётся (Senior его игнорирует)
- ❌ Strategy.accent_color часто возвращает дефолтный #0066CC — слабая экстракция цвета
- ❌ config.py: MODEL_INSPECTOR и MODEL_CHEAP указывают на gemini-3.1-flash-lite-preview (404)

## Окружение
- Windows, PowerShell, VS Code + Continue, Python 3.14
- SDK: google-genai, Vertex AI ($300 credits)
- Модели: gemini-2.5-flash, gemini-2.5-pro
- LibreOffice 26.2, Poppler 25.12, gcloud CLI

## Модели (config.py)
- MODEL_CLASSIFIER: gemini-2.5-flash (используется Classifier + Strategy Director)
- MODEL_BRAIN: gemini-2.5-pro (Senior Designer)
- MODEL_DESIGNER: gemini-2.5-pro (Junior Designer)
- MODEL_VISION: gemini-2.5-flash (зарезервировано)
- MODEL_INSPECTOR: gemini-2.5-flash (сменить с 3.1-flash-lite)
- MODEL_CHEAP: gemini-2.5-flash-lite (сменить с 3.1-flash-lite)

## Команда
- **Tech Lead (Claude)** — логика, архитектура, код целиком
- **Operator (Алишер)** — новичок, открывает файлы, копирует код, нажимает кнопки
- ~~Junior Dev (Continue + Gemini)~~ — больше НЕ используем, сжирает токены

## Формат ответа Техлида
1. 📁 Файл: точное имя
2. 🖱️ Действие для Оператора (открыть/выделить/вставить)
3. 💾 Готовый код целиком (копируй и вставляй, никакого Ctrl+I)
4. 🧠 Примечание (опционально)

## Правила
- Экономим токены и деньги — не запускаем тесты без необходимости
- Тесты только на 1 слайде (`--slides=0`), потом расширяем
- Перед правкой большого файла — Techlead обязан прочитать его актуальную версию
- PowerShell: команды по одной
- Никаких изменений в файлах, которые Techlead не читал
- GitHub: https://github.com/secrettk98/secrettk98/pptx-ai

## Ключевые файлы
- **core/orchestrator.py** — главный пайплайн (Strategy → Classifier → Senior → Junior)
- **core/llm_client.py** — вызовы API (sync + async, system_instruction, мульти-изображения)
- **core/prompt_assembler.py** — сборка модульных промптов из config/ по классификации
- **core/llm_normalize.py** — нормализация ответов AI под Pydantic
- **core/grid_calculator.py** — НЕ подключён, будем дорабатывать как LayoutEngine
- **core/ollama_client.py** — оставлен на будущее для простых задач
- **agents/strategy_director.py** — единая стратегия на всю презентацию
- **agents/classifier.py** — классификация (батч/поштучно с vision)
- **agents/senior_designer.py** — LayoutPlan (батч/поштучно)
- **agents/junior_designer.py** — SVG генерация (async)
- **models/contracts.py** — Pydantic модели (отчищены, 12 активных классов)
- **parsers/pptx_parser.py** — parse_pptx_rich (старый parse_pptx удалён)
- **parsers/slide_renderer.py** — PPTX → JPG через LibreOffice
- **config/** — правила дизайн-системы (.md модули)
- **prompts/** — промпты агентов (.md)
- **reverse/** — модули реверса (карта работает на 80%, не подключена)

## Активные контракты (models/contracts.py)
GroupPosition, ShapeStyle, ParsedShape, ParsedSlide, ParsedPresentation,
ClientConstraints, SlideClassificationV2,
PresentationStrategy,
ColumnInstruction, RowInstruction, FooterInstruction, LayoutPlan,
DesignedSlide