from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User, Message, CallbackQuery
from app.utils import get_logger


def _get_event_details(event: TelegramObject) -> str:
    """Извлечение деталей события для логирования."""
    if isinstance(event, Message):
        if event.text:
            return f"Текст: {event.text[:50]}{'...' if len(event.text) > 50 else ''}"
        elif event.sticker:
            return f"Стикер: {event.sticker.file_id}"
        elif event.photo:
            return "Фото"
        elif event.document:
            return f"Документ: {event.document.file_name or event.document.file_id}"
        return "Сообщение без текста"
    elif isinstance(event, CallbackQuery):
        return f"Callback: {event.data or 'без данных'}"
    return "Неизвестное событие"


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех входящих событий."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)

    async def __call__(self, handler, event: TelegramObject, data: dict) -> None:
        """Логирование входящих событий и обработка ошибок."""
        user: User = data.get("event_from_user")
        event_type = type(event).__name__
        event_details = _get_event_details(event)

        try:
            if user:
                self.logger.debug(
                    f"Событие '{event_type}' от пользователя {user.id} ({user.first_name}): {event_details}"
                )
            else:
                self.logger.debug(f"Событие '{event_type}' без пользователя: {event_details}")

            result = await handler(event, data)
            return result

        except Exception as e:
            self.logger.error(
                f"Ошибка при обработке события '{event_type}' "
                f"{'от пользователя ' + str(user.id) if user else 'без пользователя'}: {str(e)}",
                exc_info=True
            )
            raise

