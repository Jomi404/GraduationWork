from app.core.database import engine, Base

from app.handlers.user.models import Agree_Policy
from app.handlers.models import Privacy_Policy, Special_Equipment_Category, Special_Equipment, Equipment_Rental_History
from app.utils import get_logger

logger = get_logger(__name__)


async def init_db():
    logger.debug("Начало инициализации таблиц в базе данных")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.debug("Таблицы успешно созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {str(e)}")
        raise
