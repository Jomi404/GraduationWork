from sqlalchemy.ext.asyncio import AsyncSession
from app.handlers.dao import SpecialEquipmentCategoryDAO, SpecialEquipmentDAO
from app.utils.logging import get_logger
from app.handlers.schemas import SpecialEquipmentCreate

logger = get_logger(__name__)


async def generate_default_equipment(session: AsyncSession) -> None:
    """Проверяет, пуста ли таблица special_equipments, и если да, генерирует по 4 записи для каждой категории."""
    logger.debug("Запуск generate_default_equipment")

    equipment_dao = SpecialEquipmentDAO(session)
    existing_equipment = await equipment_dao.find_all()
    if existing_equipment:
        logger.debug(f"Таблица special_equipments уже содержит записи: {len(existing_equipment)}")
        return

    logger.debug("Таблица special_equipments пуста. Генерируем дефолтные записи.")

    category_dao = SpecialEquipmentCategoryDAO(session)
    categories = await category_dao.find_all()
    if not categories:
        logger.warning("Категории отсутствуют. Пропускаем генерацию техники.")
        return

    default_image_url = "https://iimg.su/i/Tx3v8r"
    default_equipment = []

    for category in categories:
        category_id = category.id
        category_name = category.name.lower()
        for i in range(1, 5):
            name = f"{category_name} Модель {i}"
            description = f"Описание для {name}"
            rental_price_per_day = 5000.00 + (i * 1000.00)
            equipment_data = SpecialEquipmentCreate(
                name=name,
                description=description,
                rental_price_per_day=rental_price_per_day,
                category_id=category_id,
                technical_specs={"power": f"{100 + i * 10} hp"},
                image_path=default_image_url
            )
            default_equipment.append(equipment_data)

    for equipment in default_equipment:
        await equipment_dao.add(equipment)

    await session.commit()
    logger.debug(f"Сгенерировано {len(default_equipment)} записей в таблице special_equipments")

