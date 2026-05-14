"""Централизованный модуль для настройки логирования компонентов системы."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Инициализирует и возвращает логгер с выводом в консоль для указанного модуля."""
    try:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
                datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    except Exception as error:
        raise RuntimeError(f"Не удалось инициализировать логгер {name}: {error}") from error


# Пример использования:
# from core.logger import get_logger
# log = get_logger(__name__)
# log.info("Парсинг завершён")