from abc import ABC, abstractmethod
from aiogram import Router
from app.utils.logging import get_logger


class BaseHandler(ABC):
    """Абстрактный базовый класс для обработчиков команд."""

    def __init__(self, dp: Router):
        self.dp = dp
        self.logger = get_logger(self.__class__.__name__)
        self.register_handlers()

    @abstractmethod
    def register_handlers(self):
        """Метод для регистрации обработчиков команд."""
        pass