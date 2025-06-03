from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict, HttpUrl


class TelegramIDModel(BaseModel):
    telegram_id: int

    model_config = ConfigDict(from_attributes=True)


class PrivacyPolicyFilter(BaseModel):
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentCategoryBase(BaseModel):
    """Базовая схема для общих полей категории спецтехники.
    Используется для избежания дублирования кода в Create, Update, Read схемах.
    """
    description: Optional[str] = None
    path_image: Optional[str] = "https://iimg.su/i/Tx3v8r"


class SpecialEquipmentCategoryCreate(SpecialEquipmentCategoryBase):
    """Схема для создания новой категории спецтехники.
    Используется в POST-запросах для валидации входных данных.
    Требует name (обязательное поле), опционально description и path_image.
    Пример: {"name": "Экскаваторы", "description": "Гусеничные и колесные экскаваторы", "path_image": "https://iimg.su/i/Tx3v8r"}
    """
    name: str
    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentCategoryUpdate(SpecialEquipmentCategoryBase):
    """Схема для обновления существующей категории спецтехники.
    Используется в PATCH/PUT-запросах для частичного или полного обновления.
    Все поля опциональны, чтобы клиент мог обновить только часть данных.
    Пример: {"name": "Новые экскаваторы", "path_image": "https://iimg.su/i/NewImage"}
    """
    name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentCategoryRead(SpecialEquipmentCategoryBase):
    """Схема для чтения данных о категории спецтехники.
    Используется в GET-запросах для сериализации ответа API.
    Включает автоматически генерируемые поля (id, created_at, updated_at).
    Пример ответа: {"id": 1, "name": "Экскаваторы", "description": null, "path_image": "https://iimg.su/i/Tx3v8r", "created_at": "2025-05-19T07:30:00", "updated_at": "2025-05-19T07:30:00"}
    """
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SpecialEquipmentCategoryCatId(BaseModel):
    category_id: int


class SpecialEquipmentCategoryId(BaseModel):
    id: Optional[int] = None


class SpecialEquipmentIdFilter(BaseModel):
    id: int


class SpecialEquipmentIdFilterName(BaseModel):
    name: str


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


class RequestStatusBase(BaseModel):
    """Базовая схема для общих полей статуса заявки."""
    name: str


class RequestStatusCreate(RequestStatusBase):
    """Схема для создания нового статуса заявки."""
    model_config = ConfigDict(from_attributes=True)


class RequestStatusUpdate(BaseModel):
    """Схема для обновления статуса заявки."""
    name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class RequestStatusRead(RequestStatusBase):
    """Схема для чтения статуса заявки."""
    id: int
    model_config = ConfigDict(from_attributes=True)


class RequestBase(BaseModel):
    """Базовая схема для общих полей заявки."""
    tg_id: int
    equipment_name: str
    selected_date: datetime
    phone_number: str
    address: str
    first_name: str
    username: str
    status_id: int


class RequestCreate(BaseModel):
    """Схема для создания новой заявки."""
    tg_id: int
    equipment_name: str
    selected_date: datetime
    phone_number: str
    address: str
    first_name: Optional[str] = None
    username: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class RequestUpdate(BaseModel):
    """Схема для обновления заявки."""
    tg_id: Optional[int] = None
    equipment_name: Optional[str] = None
    selected_date: Optional[datetime] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    first_name: Optional[str] = None
    username: Optional[str] = None
    status_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class RequestRead(RequestBase):
    """Схема для чтения заявки."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RequestFilter(BaseModel):
    id: Optional[int] = None
    tg_id: Optional[int] = None
    status_id: Optional[int] = None


class CompanyContactBase(BaseModel):
    """Базовая схема для общих полей контактной информации компании."""
    company_name: str
    description: Optional[str] = None
    phone: str
    email: str
    telegram: str
    address: Optional[str] = None
    work_hours: Optional[str] = None
    website: Optional[HttpUrl] = None
    social_media: Optional[str] = None
    requisites: Optional[str] = None
    image_url: Optional[HttpUrl] = "https://iimg.su/i/7vTQV5"


class CompanyContactCreate(CompanyContactBase):
    """Схема для создания новой записи контактной информации."""
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


class CompanyContactUpdate(BaseModel):
    """Схема для обновления контактной информации."""
    company_name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    telegram: Optional[str] = None
    address: Optional[str] = None
    work_hours: Optional[str] = None
    website: Optional[HttpUrl] = None
    social_media: Optional[str] = None
    requisites: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    is_active: Optional[bool] = None
    model_config = ConfigDict(from_attributes=True)


class CompanyContactRead(CompanyContactBase):
    """Схема для чтения контактной информации."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CompanyContactFilter(BaseModel):
    """Схема для фильтрации контактной информации."""
    is_active: Optional[bool] = True
    model_config = ConfigDict(from_attributes=True)
