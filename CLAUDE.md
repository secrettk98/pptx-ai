# PPTX-AI — Project Context

## Продукт
B2B AI-сервис редизайна и генерации презентаций PowerPoint. PPTX + акцент → AI → нативный редактируемый PPTX.

## Принцип
LLM — мозг (анализ, выбор layout, бриф). Python — руки (парсинг, сборка). Только нативные элементы PowerPoint, никаких PNG/PDF.

## Архитектура v2 (МАЙ 2026)

1. **Parser [Python]** → JSON_PARSED
2. **Vision [AI]** → JSON_VISION (опционально, с картинкой)
3. **Classifier [AI]** → SlideClassificationV2 (батч до 20)
4. **Senior Designer [AI]** → LayoutPlan (батч до 10)
5. **Junior Designer [AI]** → SVG (async, до 5 параллельно)
6. **Reverse block** → Map / Chart / Scheme / Image
7. **Валидатор [Python]** → программная проверка (TODO)
8. **Inspector [AI]** → визуальная проверка → цикл (TODO)
9. SVG Engine → PPTX → Постобработка → Клиент

## Что работает
- ✅ Полный пайплайн: Parser → Classifier → Senior → Junior → SVG
- ✅ Orchestrator v2 с кэшем, батчами, async
- ✅ system_instruction во всех агентах
- ✅ SVG Engine, Постпроцессоры
- ✅ Реверс карт ~80% (не подключён)
- ✅ google.genai SDK + Vertex AI (project: powermagic, us-central1)
- ✅ Дизайн-система: 12-колоночная сетка, модульные промпты

## Известные проблемы
- ❌ Junior плохо центрирует контент вертикально
- ❌ Senior иногда кладёт карточки в одну колонку вместо разделения
- ❌ Senior создаёт лишние text-ряды для коротких подзаголовков
- ❌ config.py: некоторые модели 404 в Vertex AI

## Окружение
- Windows, PowerShell, VS Code + Continue, Python 3.14
- SDK: google-genai, Vertex AI ($300 credits)
- Модели: gemini-2.5-flash, gemini-2.5-pro
- LibreOffice 26.2, Poppler 25.12, gcloud CLI

## Модели (config.py)
- MODEL_VISION: gemini-2.5-flash
- MODEL_CLASSIFIER: gemini-2.5-flash
- MODEL_BRAIN: gemini-2.5-pro
- MODEL_DESIGNER: gemini-2.5-pro
- MODEL_INSPECTOR: gemini-2.5-flash (сменить с 3.1-flash-lite)
- MODEL_CHEAP: gemini-2.5-flash-lite (сменить с 3.1-flash-lite)

## Команда
- **Tech Lead (Claude)** — логика, архитектура
- **Operator (Алишер)** — новичок, открывает файлы, нажимает кнопки
- **Junior Dev (Continue + Gemini)** — пишет код по промптам (Ctrl+I)

## Формат ответа Техлида:
1. 📁 Файл: точное имя
2. 🖱️ Действие для Оператора
3. 🤖 Промпт для Джуниора (Ctrl+I)
4. 🧠 Примечание (опционально)

## Правила
- Экономим токены
- PowerShell: команды по одной
- GitHub: https://github.com/secrettk98/pptx-ai

## Ключевые файлы
- core/orchestrator.py — главный пайплайн
- core/llm_client.py — вызовы API (sync + async, system_instruction)
- core/prompt_assembler.py — сборка промптов из config/
- agents/classifier.py — классификация (батч/поштучно)
- agents/senior_designer.py — LayoutPlan (батч/поштучно)
- agents/junior_designer.py — SVG генерация (async)
- models/contracts.py — все Pydantic модели
- config/ — правила дизайн-системы (.md)
- prompts/ — промпты агентов (.md)