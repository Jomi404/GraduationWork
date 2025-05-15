from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.core.database import connection
from app.handlers.schemas import TelegramIDModel
from app.handlers.admin.dao import AdminDAO
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AdminFilter(BaseFilter):
    """Фильтр для проверки, является ли пользователь администратором."""

    @connection()
    async def __call__(self, message: Message, session, **kwargs) -> bool:
        """Проверяет, есть ли tg_id пользователя в таблице Admin."""
        telegram_id = message.from_user.id
        logger.debug(f"Проверка статуса администратора для tg_id={telegram_id}")

        try:
            admin_dao = AdminDAO(session)
            admin = await admin_dao.find_one_or_none(TelegramIDModel(telegram_id=telegram_id))
            is_admin = admin is not None
            logger.info(f"Пользователь tg_id={telegram_id} {'является' if is_admin else 'не является'} администратором")
            return is_admin
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса администратора для tg_id={telegram_id}: {str(e)}", exc_info=True)
            return False
