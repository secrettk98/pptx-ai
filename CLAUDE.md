# PPTX-AI — Project Context

## Продукт
B2B AI-сервис редизайна и генерации презентаций PowerPoint. PPTX + акцент → AI → нативный редактируемый PPTX.

## Принцип
LLM — мозг (анализ, выбор layout, бриф). Python — руки (парсинг, сборка). Только нативные элементы PowerPoint, никаких PNG/PDF.

## Архитектура v2 (МАЙ 2026)

1. **Parser [Python]** → JSON_PARSED (объекты, типы, расположение)
2. **Vision [AI]** → JSON_VISION (умная группировка, описание сложных элементов)
3. **Classifier [AI]** → JSON_FINAL (объединение + тип слайда + нужные инструкции)
4. **Senior Designer [AI]** → концепция, шаблон, инструкции для Junior
5. **Junior Designer [AI]** → SVG-код с плейсхолдерами для reverse
6. **Reverse block** → Map / Scheme / Chart / Image generators
7. **Сборщик [Python]** → финальный SVG
8. **Валидатор [Python]** → программная проверка
9. **Inspection [AI]** → визуальная проверка → возврат к Senior (макс 2 итерации)
10. SVG Engine → PPTX → Постобработка → Клиент

## Что работает
- ✅ Parser, Конвертер JPG, Vision-классификатор, Brain (→ станет Senior), Designer (→ станет Junior)
- ✅ SVG Engine, Постпроцессоры SVG + PPTX
- ✅ Реверс карт ~80% (не подключён к оркестратору)
- ✅ google.genai SDK + Vertex AI (project: powermagic, us-central1)

## Что нужно сделать
- Classifier (новый агент), Senior Designer, Junior Designer, Валидатор, Inspection
- Подключить reverse-модули, цикл обратной связи

## Окружение
- Windows, PowerShell, VS Code + Continue, Python 3.14
- SDK: google-genai, Vertex AI ($300 credits)
- Модели: gemini-2.5-flash, gemini-2.5-pro, gemini-2.5-flash-lite
- НЕ работает в Vertex AI: gemini-3.1-flash-lite-preview (404)
- LibreOffice 26.2, Poppler 25.12, gcloud CLI

## Модели (config.py)
- MODEL_VISION: gemini-2.5-flash
- MODEL_BRAIN: gemini-2.5-flash
- MODEL_DESIGNER: gemini-2.5-pro
- MODEL_INSPECTOR: gemini-2.5-flash
- MODEL_CHEAP: gemini-2.5-flash-lite

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
- Экономим токены, бюджет чата: 200 000
- PowerShell: команды по одной
- GitHub: https://github.com/secrettk98/pptx-ai

## Актуальные проблемы
- Качество SVG нестабильно — нужна архитектура Senior+Junior
- SVG text word-wrap — tspan в промпте, не всегда соблюдается
- Постпроцессор скругляет ВСЕ Rectangle