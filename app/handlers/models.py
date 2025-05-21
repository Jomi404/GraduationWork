from datetime import datetime
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
        created_at: datetime - Временная метка создания категории.
        updated_at: datetime - Временная метка последнего обновления категории.
    """
    __tablename__ = "special_equipment_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
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
    image_path: Mapped[str] = mapped_column(String(255), nullable=True)  # <-- Добавлено поле

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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Связь с таблицей Special_Equipment
    equipment: Mapped["Special_Equipment"] = relationship(back_populates="rental_history")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, equipment_id={self.equipment_id})>"


# Определение индексов
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

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, tg_id={self.tg_id}, status_id={self.status_id})>"
