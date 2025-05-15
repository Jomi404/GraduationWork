from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.core.database import connection
from app.handlers.schemas import TelegramIDModel, PrivacyPolicyFilter
from app.handlers.user.dao import AgreePolicyDAO
from app.handlers.dao import PrivacyPolicyDAO
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def get_active_policy_url(session) -> str:
    """Получает URL активной политики конфиденциальности из базы данных."""
    try:
        policy_dao = PrivacyPolicyDAO(session)
        active_policy = await policy_dao.find_one_or_none(PrivacyPolicyFilter(is_active=True))
        if active_policy:
            logger.info(f"Найдена активная политика конфиденциальности с URL: {active_policy.url}")
            return active_policy.url
        logger.warning("Активная политика конфиденциальности не найдена в базе данных")
        return "https://graph.org/Politika-konfidencialnosti-05-05-8"  # Резервный URL
    except Exception as e:
        logger.error(f"Ошибка при получении активной политики конфиденциальности: {str(e)}", exc_info=True)
        return "https://graph.org/Politika-konfidencialnosti-05-05-8"  # Резервный URL при ошибке


class AgreePolicyFilter(BaseFilter):
    """Фильтр для проверки, согласился ли пользователь с политикой конфиденциальности."""

    @connection()
    async def __call__(self, message: Message, session, **kwargs) -> bool:
        """Проверяет, есть ли tg_id пользователя в таблице Agree_Policy."""
        telegram_id = message.from_user.id
        logger.debug(f"Проверка согласия с политикой конфиденциальности для tg_id={telegram_id}")

        try:
            policy_dao = AgreePolicyDAO(session)
            policy = await policy_dao.find_one_or_none(TelegramIDModel(telegram_id=telegram_id))
            has_agreed = policy is not None
            logger.info(f"Пользователь tg_id={telegram_id} {'согласился' if has_agreed else 'не согласился'} "
                        f"с политикой конфиденциальности")
            return has_agreed
        except Exception as e:
            logger.error(f"Ошибка при проверке согласия с политикой для tg_id={telegram_id}: {str(e)}", exc_info=True)
            return False
