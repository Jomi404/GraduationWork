from aiogram.filters import BaseFilter
from aiogram.types import Message
from aiogram_dialog import DialogManager
from sqlalchemy import select

from app.core.database import connection, get_session
from app.handlers.schemas import TelegramIDModel, PrivacyPolicyFilter, SpecialEquipmentCategoryCatId, \
    SpecialEquipmentIdFilter
from app.handlers.user.dao import AgreePolicyDAO
from app.handlers.dao import PrivacyPolicyDAO, SpecialEquipmentCategoryDAO, SpecialEquipmentDAO
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
        return "https://graph.org/Politika-konfidencialnosti-05-05-8"
    except Exception as e:
        logger.error(f"Ошибка при получении активной политики конфиденциальности: {str(e)}", exc_info=True)
        return "https://graph.org/Politika-konfidencialnosti-05-05-8"


class AgreePolicyFilter(BaseFilter):
    @connection()
    async def __call__(self, message: Message, session, **kwargs) -> bool:
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


async def async_get_category_buttons(dialog_manager: DialogManager, **kwargs) -> dict:
    middleware_logger = dialog_manager.middleware_data.get("logger")
    active_logger = middleware_logger if middleware_logger else logger
    active_logger.debug("Начало выполнения async_get_category_buttons")

    # Параметры пагинации
    items_per_page = 5
    current_page = dialog_manager.dialog_data.get("category_page", 0)
    cache_key = "cached_all_categories"

    # Проверяем кэш всех категорий
    if cache_key in dialog_manager.dialog_data:
        all_categories = dialog_manager.dialog_data[cache_key]
        active_logger.debug(f"Используются кэшированные категории (всего: {len(all_categories)})")
    else:
        async with get_session() as session:
            category_dao = SpecialEquipmentCategoryDAO(session)
            categories = await category_dao.find_all()
            all_categories = [
                (category.name, category.id) for category in categories
                if hasattr(category, 'id') and hasattr(category, 'name')
            ]
            active_logger.debug(f"Загруженные категории из базы данных: {all_categories}")
            dialog_manager.dialog_data[cache_key] = sorted(all_categories, key=lambda x: x[1])
            active_logger.debug(f"Кэшированы все категории: {all_categories}")

    total_categories = len(all_categories)
    total_pages = (total_categories + items_per_page - 1) // items_per_page
    active_logger.debug(f"Всего категорий: {total_categories}, страниц: {total_pages}")

    # Возвращаем полный список категорий, пагинация будет обрабатываться в ScrollingGroup
    if not all_categories and current_page == 0:
        active_logger.warning("Список категорий пуст. Возвращаются дефолтные категории.")
        all_categories = [
            ("Экскаваторы", 1),
            ("Бульдозеры", 2),
            ("Краны", 3),
            ("Самосвалы", 4),
            ("Тракторы", 5),
            ("Манипуляторы", 6)
        ]
        total_categories = len(all_categories)
        total_pages = (total_categories + items_per_page - 1) // items_per_page
        active_logger.debug(f"Дефолтные категории: {all_categories}, всего страниц: {total_pages}")

    dialog_manager.dialog_data["total_category_pages"] = total_pages
    active_logger.info(f"Подготовлены категории: {all_categories}")

    return {
        "categories": all_categories,  # Возвращаем полный список категорий
        "total_pages": total_pages
    }


async def async_get_equipment_buttons(dialog_manager: DialogManager, **kwargs) -> dict:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug("Calling async_get_equipment_buttons")

    category_id = dialog_manager.start_data.get("category_id")
    logger_my.debug(f"start_data: {dialog_manager.start_data}")
    if not category_id:
        logger_my.error("category_id is missing in start_data")
        return {"equipment": [], "total_pages": 1}

    items_per_page = 5
    current_page = dialog_manager.dialog_data.get(f"equipment_page_{category_id}", 0)
    cache_key = f"cached_equipment_{category_id}"

    if cache_key in dialog_manager.dialog_data:
        all_equipment = dialog_manager.dialog_data[cache_key]
        logger_my.debug(
            f"Используются кэшированные данные оборудования для category_id={category_id}, всего: {len(all_equipment)}")
    else:
        async with get_session() as session:
            equipment_dao = SpecialEquipmentDAO(session)
            equipment = await equipment_dao.find_all(SpecialEquipmentCategoryCatId(category_id=category_id))
            all_equipment = [(equip.name, str(equip.id)) for equip in equipment]
            dialog_manager.dialog_data[cache_key] = all_equipment
            logger_my.debug(f"Кэшировано оборудование для category_id={category_id}: {all_equipment}")

    total_equipment = len(all_equipment)
    total_pages = (total_equipment + items_per_page - 1) // items_per_page

    # Возвращаем полный список оборудования
    dialog_manager.dialog_data[f"total_equipment_pages_{category_id}"] = total_pages
    logger_my.debug(f"Подготовлены данные оборудования: {all_equipment}")

    return {"equipment": all_equipment, "total_pages": total_pages}


async def async_get_equipment_details(dialog_manager: DialogManager, **kwargs) -> dict:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug("Calling async_get_equipment_details")

    start_data = dialog_manager.start_data
    equipment_id = start_data.get("equipment_id")

    if not equipment_id:
        logger_my.error("equipment_id is missing in start_data")
        return {"equipment_name": "Неизвестно", "rental_price": 0, "description": "Нет данных"}

    async with get_session() as session:
        equipment_dao = SpecialEquipmentDAO(session)
        equipment = await equipment_dao.find_one_or_none(SpecialEquipmentIdFilter(id=equipment_id))
        if not equipment:
            logger_my.error(f"Техника с id={equipment_id} не найдена")
            return {"equipment_name": "Неизвестно", "rental_price": 0, "description": "Нет данных"}

        return {
            "equipment_name": equipment.name,
            "rental_price": float(equipment.rental_price_per_day),
            "description": equipment.description or "Нет описания"
        }
