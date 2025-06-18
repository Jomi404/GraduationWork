from sqlalchemy.orm import selectinload

from app.core.base_dao import BaseDAO
from app.handlers.models import Privacy_Policy, Special_Equipment_Category, Special_Equipment, \
    Equipment_Rental_History, Request_Status, Request, CompanyContact, PaymentTransaction, User, UserStatus
from app.handlers.schemas import RequestStatusBase, RequestCreate, SpecialEquipmentIdFilterName, CompanyContactFilter, \
    TelegramIDModel
from app.utils import get_logger

logger = get_logger(__name__)


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

    async def find_by_name(self, name: str) -> Special_Equipment | None:
        """Найти оборудование по имени."""
        filters = SpecialEquipmentIdFilterName(name=name)
        return await self.find_one_or_none(filters)


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


class RequestStatusDAO(BaseDAO[Request_Status]):
    """Объект доступа к данным (DAO) для управления записями Request_Status."""
    model = Request_Status


class RequestDAO(BaseDAO[Request]):
    """Объект доступа к данным (DAO) для управления записями Requests."""
    model = Request

    async def add(self, values: 'RequestCreate'):
        values_dict = values.model_dump(exclude_unset=True)
        status_dao = RequestStatusDAO(self._session)
        status = await status_dao.find_one_or_none(filters=RequestStatusBase(name="Новая"))
        if not status:
            raise ValueError("Статус 'Новая' не найден в базе данных")
        values_dict["status_id"] = status.id
        new_instance = self.model(**values_dict)
        self._session.add(new_instance)
        try:
            re = await self._session.flush()
            logger.info(f're {re}')
        except Exception as e:
            logger.error(f"Ошибка при flush: {e}")
            raise
        return new_instance


class CompanyContactDAO(BaseDAO[CompanyContact]):
    """Объект доступа к данным (DAO) для управления записями CompanyContact.

    Этот класс предоставляет методы для выполнения CRUD-операций над моделью CompanyContact,
    которая хранит контактную информацию компании.
    Наследуется от BaseDAO, обеспечивающего общие операции с базой данных.

    Использование:
        dao = CompanyContactDAO(session)
        async with async_session_maker() as session:
            contact = await dao.add({
                "company_name": "СпецТехАренда",
                "phone": "+78001234567",
                "email": "support@specteharenda.ru",
                "telegram": "@SpecTehSupport"
            }, session=session)
    """
    model = CompanyContact

    async def get_active_contact(self) -> CompanyContact | None:
        """Получить активную контактную информацию."""
        filters = CompanyContactFilter(is_active=True)
        return await self.find_one_or_none(filters)


class PaymentTransactionDAO(BaseDAO[PaymentTransaction]):
    """Объект доступа к данным (DAO) для управления записями PaymentTransaction."""
    model = PaymentTransaction


class UserDAO(BaseDAO[User]):
    model = User

    async def find_by_telegram_id(self, telegram_id: int) -> User | None:
        """Найти пользователя по telegram_id с предзагрузкой статуса."""
        filters = TelegramIDModel(telegram_id=telegram_id)
        return await self.find_one_or_none(filters, options=[selectinload(User.status)])


class UserStatusDAO(BaseDAO[UserStatus]):
    """Объект доступа к данным (DAO) для управления записями UserStatus."""
    model = UserStatus
