from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Text, Integer, ForeignKey, Numeric, Index, TIMESTAMP, DECIMAL, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Privacy_Policy(Base):
    """Модель для хранения политики конфиденциальности.
    Поля:
        id: int - Уникальный идентификатор записи.
        url: str - URL-адрес, где размещена политика.
        version: str - Версия политики (например, "1.0").
        is_active: bool - Флаг, указывающий на активную версию политики.
    """
    __tablename__ = "privacy_policies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"


class Special_Equipment_Category(Base):
    """Модель для хранения категорий спецтехники.
    Поля:
        id: int - Уникальный идентификатор категории.
        name: str - Название категории (уникальное).
        description: str - Необязательное описание категории.
        path_image: str - Путь к изображению категории (по умолчанию: https://iimg.su/i/Tx3v8r).
        created_at: datetime - Временная метка создания категории.
        updated_at: datetime - Временная метка последнего обновления категории.
    """
    __tablename__ = "special_equipment_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    path_image: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="https://iimg.su/i/Tx3v8r",
        server_default="https://iimg.su/i/Tx3v8r"
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Связь с таблицей Special_Equipment
    equipment: Mapped[list["Special_Equipment"]] = relationship(
        back_populates="category", cascade="all, delete"
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name})>"


class Special_Equipment(Base):
    """Модель для хранения данных о спецтехнике.
    Поля:
        id: int - Уникальный идентификатор оборудования.
        name: str - Название оборудования (уникальное).
        description: str - Необязательное описание оборудования.
        rental_price_per_day: decimal - Стоимость аренды за день.
        category_id: int - Внешний ключ, ссылающийся на категорию.
        technical_specs: jsonb - Технические характеристики в формате JSON.
        image_path: str - Путь до изображения оборудования.
        created_at: datetime - Временная метка создания оборудования.
        updated_at: datetime - Временная метка последнего обновления оборудования.
    """
    __tablename__ = "special_equipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    rental_price_per_day: Mapped[DECIMAL] = mapped_column(Numeric(10, 2), nullable=False)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("special_equipment_categories.id", ondelete="RESTRICT"),
        nullable=False
    )
    technical_specs: Mapped[dict] = mapped_column(JSONB, nullable=True)
    image_path: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    category: Mapped["Special_Equipment_Category"] = relationship(back_populates="equipment")
    rental_history: Mapped[list["Equipment_Rental_History"]] = relationship(
        back_populates="equipment", cascade="all, delete"
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name})>"


class Equipment_Rental_History(Base):
    """Модель для хранения истории аренды спецтехники.
    Поля:
        id: int - Уникальный идентификатор записи об аренде.
        equipment_id: int - Внешний ключ, ссылающийся на оборудование.
        start_date: datetime - Дата начала аренды.
        end_date: datetime - Дата окончания аренды (необязательно).
        rental_price_at_time: decimal - Стоимость аренды на момент аренды.
        created_at: datetime - Временная метка создания записи.
    """
    __tablename__ = "equipment_rental_histories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("special_equipments.id", ondelete="CASCADE"),
        nullable=False
    )
    start_date: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    end_date: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)
    rental_price_at_time: Mapped[DECIMAL] = mapped_column(Numeric(10, 2), nullable=False)
    total_work_time: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    equipment: Mapped["Special_Equipment"] = relationship(back_populates="rental_history")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, equipment_id={self.equipment_id})>"


Index("idx_equipment_category_id", Special_Equipment.category_id)
Index("idx_rental_history_equipment_id", Equipment_Rental_History.equipment_id)
Index("idx_rental_history_dates", Equipment_Rental_History.start_date, Equipment_Rental_History.end_date)


class Request_Status(Base):
    """Модель для хранения статусов заявок."""
    __tablename__ = "request_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name})>"


class Request(Base):
    """Модель для хранения заявок."""
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    equipment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    selected_date: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("request_statuses.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )

    status: Mapped["Request_Status"] = relationship("Request_Status")
    payment_transactions: Mapped[list["PaymentTransaction"]] = relationship(
        back_populates="request", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, tg_id={self.tg_id}, status_id={self.status_id})>"


class CompanyContact(Base):
    """Модель для хранения контактной информации компании.
    Поля:
        id: int - Уникальный идентификатор записи.
        company_name: str - Название компании.
        description: str - Краткое описание компании.
        phone: str - Контактный телефон.
        email: str - Контактный email.
        telegram: str - Ссылка на Telegram-канал или чат поддержки.
        address: str - Адрес офиса компании.
        work_hours: str - График работы.
        website: str - Ссылка на сайт компании (опционально).
        social_media: str - Ссылки на социальные сети (опционально).
        requisites: str - Реквизиты компании (опционально).
        image_url: str - URL изображения для окна контактов (по умолчанию: https://iimg.su/i/7vTQV5).
        is_active: bool - Флаг активности записи.
        created_at: datetime - Временная метка создания записи.
        updated_at: datetime - Временная метка последнего обновления записи.
    """
    __tablename__ = "company_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    telegram: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=True)
    work_hours: Mapped[str] = mapped_column(String(100), nullable=True)
    website: Mapped[str] = mapped_column(String(255), nullable=True)
    social_media: Mapped[str] = mapped_column(Text, nullable=True)  # Например, JSON-строка или текст с ссылками
    requisites: Mapped[str] = mapped_column(Text, nullable=True)  # Например, ИНН, ОГРН
    image_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="https://iimg.su/i/7vTQV5",
        server_default="https://iimg.su/i/7vTQV5"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, company_name={self.company_name})>"


class PaymentTransaction(Base):
    """Модель для хранения информации о транзакциях оплаты.
    Поля:
        id: int - Уникальный идентификатор транзакции.
        request_id: int - Внешний ключ, ссылающийся на заявку.
        transaction_id: str - Уникальный идентификатор транзакции в Юкасса.
        amount: Decimal - Сумма оплаты.
        status: str - Статус транзакции (например, 'pending', 'success', 'failed').
        created_at: datetime - Временная метка создания транзакции.
    """
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    request: Mapped["Request"] = relationship("Request", back_populates="payment_transactions")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, request_id={self.request_id}, status={self.status})>"


class UserStatus(Base):
    """Модель для хранения статусов пользователей."""
    __tablename__ = "user_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, status={self.status})>"


class User(Base):
    """Модель для хранения данных о пользователях."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_statuses.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )

    status: Mapped["UserStatus"] = relationship("UserStatus")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, telegram_id={self.telegram_id}, status_id={self.status_id})>"
