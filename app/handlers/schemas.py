from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict


class TelegramIDModel(BaseModel):
    telegram_id: int

    model_config = ConfigDict(from_attributes=True)


class PrivacyPolicyFilter(BaseModel):
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentCategoryBase(BaseModel):
    # Базовая схема для общих полей категории спецтехники.
    # Используется для избежания дублирования кода в Create, Update, Read схемах.
    id: int
    description: Optional[str] = None


class SpecialEquipmentCategoryCreate(SpecialEquipmentCategoryBase):
    # Схема для создания новой категории спецтехники.
    # Используется в POST-запросах для валидации входных данных.
    # Требует name (обязательное поле) и опционально description.
    # Пример: {"name": "Экскаваторы", "description": "Гусеничные и колесные экскаваторы"}
    name: str
    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentCategoryUpdate(SpecialEquipmentCategoryBase):
    # Схема для обновления существующей категории спецтехники.
    # Используется в PATCH/PUT-запросах для частичного или полного обновления.
    # Все поля опциональны, чтобы клиент мог обновить только часть данных.
    # Пример: {"name": "Новые экскаваторы"} обновит только название.
    name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentCategoryRead(SpecialEquipmentCategoryBase):
    # Схема для чтения данных о категории спецтехники. Используется в GET-запросах для сериализации ответа API.
    # Включает автоматически генерируемые поля (id, created_at, updated_at). Пример ответа: {"id": 1,
    # "name": "Экскаваторы", "description": null, "created_at": "2025-05-19T07:30:00", "updated_at":
    # "2025-05-19T07:30:00"}
    id: int
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentCategoryCatId(BaseModel):
    category_id: int


class SpecialEquipmentCategoryId(BaseModel):
    id: Optional[int] = None


class SpecialEquipmentIdFilter(BaseModel):
    id: int


class SpecialEquipmentBase(SpecialEquipmentCategoryId):
    # Базовая схема для общих полей спецтехники.
    # Содержит поля, общие для создания, обновления и чтения.
    name: str
    description: Optional[str] = None
    rental_price_per_day: Decimal
    category_id: int
    technical_specs: Optional[Dict] = None
    image_path: Optional[str] = None  # Добавлено новое поле


class SpecialEquipmentCreate(SpecialEquipmentBase):
    # Схема для создания новой единицы спецтехники.
    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentUpdate(SpecialEquipmentBase):
    # Схема для обновления существующей единицы спецтехники.
    name: Optional[str] = None
    description: Optional[str] = None
    rental_price_per_day: Optional[Decimal] = None
    category_id: Optional[int] = None
    technical_specs: Optional[Dict] = None
    image_path: Optional[str] = None  # Добавлено новое поле
    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentRead(SpecialEquipmentBase):
    # Схема для чтения данных о спецтехнике.
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EquipmentRentalHistoryBase(BaseModel):
    # Базовая схема для общих полей истории аренды.
    # Содержит поля, общие для создания, обновления и чтения.
    equipment_id: int
    start_date: datetime
    end_date: Optional[datetime] = None
    rental_price_at_time: Decimal


class EquipmentRentalHistoryCreate(EquipmentRentalHistoryBase):
    # Схема для создания новой записи об аренде.
    # Используется в POST-запросах для валидации входных данных.
    # Требует equipment_id, start_date, rental_price_at_time; end_date опционально.
    # Пример: {"equipment_id": 1, "start_date": "2025-05-19T08:00:00", "rental_price_at_time": 500.00}
    model_config = ConfigDict(from_attributes=True)


class EquipmentRentalHistoryUpdate(EquipmentRentalHistoryBase):
    # Схема для обновления записи об аренде.
    # Используется в PATCH/PUT-запросах для частичного или полного обновления.
    # Все поля опциональны для гибкого обновления.
    # Пример: {"end_date": "2025-05-20T08:00:00"} завершит аренду.
    equipment_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    rental_price_at_time: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


class EquipmentRentalHistoryRead(EquipmentRentalHistoryBase):
    # Схема для чтения данных об аренде. Используется в GET-запросах для сериализации ответа API. Включает id и
    # created_at для полной информации. Пример ответа: {"id": 1, "equipment_id": 1, "start_date":
    # "2025-05-19T08:00:00", "end_date": null, "rental_price_at_time": 500.00, ...}
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
