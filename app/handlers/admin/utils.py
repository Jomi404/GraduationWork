from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.core.database import connection
from app.handlers.dao import UserDAO
from app.utils.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class AdminFilter(BaseFilter):
    """Фильтр для проверки, является ли пользователь администратором."""

    @connection()
    async def __call__(self, message: Message, session, **kwargs) -> bool:
        """Проверяет, является ли пользователь администратором по статусу в таблице Users или по ADMIN_ROOT."""
        telegram_id = message.from_user.id
        logger.debug(f"Проверка статуса администратора для tg_id={telegram_id}")

        try:
            # Проверка, является ли пользователь супер-администратором (ADMIN_ROOT)
            admin_root_ids = settings.admin_root
            if str(telegram_id) in admin_root_ids.split(","):
                logger.debug(f"Пользователь tg_id={telegram_id} является супер-администратором (ADMIN_ROOT)")
                return True

            # Проверка статуса администратора через таблицу Users и user_statuses
            user_dao = UserDAO(session)
            user = await user_dao.find_by_telegram_id(telegram_id)
            if user and user.status.status.lower() == "админ":
                logger.debug(f"Пользователь tg_id={telegram_id} является администратором по статусу")
                return True

            logger.debug(f"Пользователь tg_id={telegram_id} не является администратором")
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса администратора для tg_id={telegram_id}: {str(e)}", exc_info=True)
            return False
