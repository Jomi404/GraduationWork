import colorlog
import logging
from pathlib import Path


def setup_logging():
    """Настройка цветного логирования для консоли и записи в файл."""
    logger = colorlog.getLogger()
    if not logger.handlers:
        # Настройка консольного обработчика с цветами
        console_handler = colorlog.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            "%(asctime)s - %(name)s - %(log_color)s%(levelname)s%(reset)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'orange',
                'ERROR': 'red',
                'CRITICAL': 'red,bold',
            }
        )
        console_handler.setFormatter(console_formatter)

        base_dir = Path(__file__).resolve().parent.parent.parent
        log_dir = base_dir / 'data' / 'log'
        log_path = log_dir / 'bot.log'

        # Настройка файлового обработчика (без цветов)
        file_handler = logging.FileHandler(log_path)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)

        # Добавление обработчиков к логгеру
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Получение логгера с заданным именем."""
    return colorlog.getLogger(name)
