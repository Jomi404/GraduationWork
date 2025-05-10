from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from app.utils import get_logger


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех входящих сообщений."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)

    async def __call__(self, handler, event: TelegramObject, data: dict) -> None:
        user: User = data.get("event_from_user")
        if user:
            self.logger.info(f"Получено сообщение от пользователя {user.id} ({user.first_name})")
        return await handler(event, data)