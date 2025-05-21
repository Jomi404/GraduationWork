import re
from aiogram.filters import BaseFilter
from aiogram.types import Message
from aiogram_dialog import DialogManager
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import connection, get_session
from app.handlers.schemas import TelegramIDModel, PrivacyPolicyFilter, SpecialEquipmentCategoryCatId, \
    SpecialEquipmentIdFilter, SpecialEquipmentIdFilterName
from app.handlers.user.dao import AgreePolicyDAO
from app.handlers.dao import PrivacyPolicyDAO, SpecialEquipmentCategoryDAO, SpecialEquipmentDAO, \
    EquipmentRentalHistoryDAO
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

    category_id = dialog_manager.start_data.get("category_id")
    if not category_id:
        logger_my.error("category_id is missing in start_data")
        return {"equipment": [], "total_pages": 1}

    items_per_page = 5
    cache_key = f"cached_equipment_{category_id}"
    pages_key = f"total_equipment_pages_{category_id}"

    if cache_key not in dialog_manager.dialog_data:
        async with get_session() as session:
            equipment_dao = SpecialEquipmentDAO(session)
            equipment = await equipment_dao.find_all(
                SpecialEquipmentCategoryCatId(category_id=category_id)
            )
            all_equipment = [(equip.name, str(equip.id)) for equip in equipment]
            dialog_manager.dialog_data[cache_key] = all_equipment
            total_pages = (len(all_equipment) + items_per_page - 1) // items_per_page
            dialog_manager.dialog_data[pages_key] = total_pages
    else:
        all_equipment = dialog_manager.dialog_data[cache_key]
        total_pages = dialog_manager.dialog_data[pages_key]

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

        dialog_manager.dialog_data.update({"equipment_name": equipment.name,
                                           "rental_price": float(equipment.rental_price_per_day)})

        return {
            "equipment_name": equipment.name,
            "rental_price": float(equipment.rental_price_per_day),
            "description": equipment.description or "Нет описания"
        }


async def check_equipment_availability(equipment_name: str, session: AsyncSession) -> dict:
    """
    Проверяет доступность техники на текущую неделю, начиная с текущего дня.

    Args:
        equipment_name (str): Название техники.
        session (AsyncSession): Сессия базы данных.

    Returns:
        dict: Словарь с информацией о доступности:
              - is_available (bool): Доступна ли техника.
              - available_dates (list): Список доступных дат в формате ISO (только текущие и будущие даты).
              - message (str): Сообщение о статусе доступности.
    """
    logger.debug(f"Проверка доступности техники: {equipment_name}")
    try:
        # Получаем ID техники по имени
        equipment_dao = SpecialEquipmentDAO(session)
        equipment = await equipment_dao.find_one_or_none(SpecialEquipmentIdFilterName(name=equipment_name))

        if not equipment:
            logger.error(f"Техника с именем {equipment_name} не найдена")
            return {
                "is_available": False,
                "available_dates": [],
                "message": f"Техника {equipment_name} не найдена"
            }

        # Определяем текущую дату и конец текущей недели (воскресенье)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_since_monday = today.weekday()  # 0 для понедельника, 1 для вторника и т.д.
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)

        # Получаем записи об аренде для техники
        rental_dao = EquipmentRentalHistoryDAO(session)
        rentals = await rental_dao.find_all()
        rentals = [
            rental for rental in rentals
            if rental.equipment_id == equipment.id
               and rental.start_date <= sunday
               and (rental.end_date is None or rental.end_date >= monday)
        ]

        logger.debug(
            f"Найденные записи об аренде для {equipment_name}: {[(r.start_date, r.end_date) for r in rentals]}")

        # Создаем список дат, начиная с сегодняшнего дня до воскресенья
        all_dates = [today + timedelta(days=i) for i in range((sunday - today).days + 1)]
        available_dates = []

        # Проверяем каждую дату на доступность
        for date in all_dates:
            is_date_available = True
            for rental in rentals:
                rental_start = rental.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                rental_end = (rental.end_date or sunday).replace(hour=0, minute=0, second=0, microsecond=0)

                # Проверяем, пересекается ли дата с периодом аренды
                if rental_start <= date <= rental_end:
                    is_date_available = False
                    logger.debug(f"Дата {date} занята: аренда с {rental_start} по {rental_end}")
                    break

            if is_date_available:
                available_dates.append(date.isoformat())
                logger.debug(f"Дата {date} доступна")

        is_available = len(available_dates) > 0
        message = (
            f"Техника {equipment_name} доступна для аренды на текущей неделе"
            if is_available
            else f"Техника {equipment_name} занята на текущей неделе"
        )

        logger.info(f"Результат проверки доступности {equipment_name}: {message}")
        logger.debug(f"Доступные даты: {available_dates}")
        return {
            "is_available": is_available,
            "available_dates": available_dates,
            "message": message
        }

    except Exception as e:
        logger.error(f"Ошибка при проверке доступности техники {equipment_name}: {str(e)}", exc_info=True)
        return {
            "is_available": False,
            "available_dates": [],
            "message": f"Ошибка при проверке доступности техники: {str(e)}"
        }


def validate_phone_number(phone: str) -> Optional[str]:
    # Удаляем все нечисловые символы
    digits = re.sub(r'\D', '', phone)
    # Проверяем различные варианты ввода
    if len(digits) == 11 and digits[0] in ['7', '8']:
        return '+7' + digits[1:]  # Например, 89930057019 -> +79930057019
    elif len(digits) == 10:
        return '+7' + digits  # Например, 9930057019 -> +79930057019
    elif len(digits) == 12 and digits.startswith('7'):
        return '+' + digits  # Например, +79930057019 -> +79930057019
    else:
        return None


def no_err_filter(data: dict, widget, manager: DialogManager) -> bool:
    return not data.get("error_message")


def is_not_available_filter(data: dict, widget, manager: DialogManager) -> bool:
    return not data.get("is_available", False)
