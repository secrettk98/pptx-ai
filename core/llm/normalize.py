"""Нормализация ответов LLM перед Pydantic-валидацией.
AI часто возвращает list вместо str, null вместо "", int вместо str.
Этот модуль чинит всё ДО того, как Pydantic увидит данные."""

import logging

logger = logging.getLogger(__name__)


def normalize_for_model(data: dict, model_class) -> dict:
    """Рекурсивно приводит data к типам, которые ожидает Pydantic-модель."""
    from pydantic import BaseModel
    import typing
    import types as builtin_types

    if not isinstance(data, dict):
        return data

    hints = typing.get_type_hints(model_class)
    result = {}

    for key, value in data.items():
        if key not in hints:
            result[key] = value
            continue

        expected = hints[key]
        origin = getattr(expected, '__origin__', None)
        args = getattr(expected, '__args__', ())

        # Убираем Optional — достаём внутренний тип
        if origin is builtin_types.UnionType or origin is typing.Union:
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                expected = non_none[0]
                origin = getattr(expected, '__origin__', None)
                args = getattr(expected, '__args__', ())

        # null → дефолт (пустая строка, пустой список, пустой dict)
        if value is None:
            if expected is str:
                value = ""
            elif origin is list:
                value = []
            elif expected is dict or origin is dict:
                value = {}
            elif expected is int or expected is float:
                value = 0
            result[key] = value
            continue

        # Ожидается str, пришёл list → join
        if expected is str and isinstance(value, list):
            value = " ".join(str(v) for v in value)
            logger.debug(f"Normalized {key}: list → str")

        # Ожидается str, пришло число
        elif expected is str and isinstance(value, (int, float)):
            value = str(value)

        # Ожидается int, пришла строка
        elif expected is int and isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                value = 0

        # Ожидается list, пришла строка → оборачиваем
        elif origin is list and isinstance(value, str):
            value = [value]

        # Ожидается list[BaseModel] → рекурсия внутрь
        elif origin is list and isinstance(value, list) and args:
            inner_type = args[0]
            if isinstance(inner_type, type) and issubclass(inner_type, BaseModel):
                value = [normalize_for_model(item, inner_type) if isinstance(item, dict) else item for item in value]

        # Ожидается BaseModel → рекурсия
        elif isinstance(expected, type) and issubclass(expected, BaseModel) and isinstance(value, dict):
            value = normalize_for_model(value, expected)

        result[key] = value

    return result
