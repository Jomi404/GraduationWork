from app.core.base_dao import BaseDAO
from app.handlers.models import Privacy_Policy, Special_Equipment_Category, Special_Equipment, Equipment_Rental_History


class PrivacyPolicyDAO(BaseDAO[Privacy_Policy]):
    model = Privacy_Policy


class SpecialEquipmentCategoryDAO(BaseDAO[Special_Equipment_Category]):
    """Объект доступа к данным (DAO) для управления записями SpecialEquipmentCategory.

    Этот класс предоставляет методы для выполнения CRUD-операций (создание, чтение, обновление, удаление)
    над моделью SpecialEquipmentCategory, которая хранит категории спецтехники.
    Наследуется от BaseDAO, обеспечивающего общие операции с базой данных.

    Использование:
        dao = SpecialEquipmentCategoryDAO()
        async with async_session_maker() as session:
            category = await dao.create({"name": "Экскаваторы"}, session=session)
    """
    model = Special_Equipment_Category


class SpecialEquipmentDAO(BaseDAO[Special_Equipment]):
    """Объект доступа к данным (DAO) для управления записями SpecialEquipment.

    Этот класс предоставляет методы для выполнения CRUD-операций над моделью SpecialEquipment,
    которая хранит данные о спецтехнике.
    Наследуется от BaseDAO, обеспечивающего общие операции с базой данных.

    Использование:
        dao = SpecialEquipmentDAO()
        async with async_session_maker() as session:
            equipment = await dao.create({
                "name": "Komatsu PC200",
                "rental_price_per_day": 500.00,
                "category_id": 1
            }, session=session)
    """
    model = Special_Equipment


class EquipmentRentalHistoryDAO(BaseDAO[Equipment_Rental_History]):
    """Объект доступа к данным (DAO) для управления записями EquipmentRentalHistory.

    Этот класс предоставляет методы для выполнения CRUD-операций над моделью EquipmentRentalHistory,
    которая хранит историю аренды спецтехники.
    Наследуется от BaseDAO, обеспечивающего общие операции с базой данных.

    Использование:
        dao = EquipmentRentalHistoryDAO()
        async with async_session_maker() as session:
            rental = await dao.create({
                "equipment_id": 1,
                "start_date": "2025-05-19T08:00:00",
                "rental_price_at_time": 500.00
            }, session=session)
    """
    model = Equipment_Rental_History
