import uuid
from functools import wraps
from typing import Annotated
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, TIMESTAMP, Integer, inspect, text
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, declared_attr
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession
from contextlib import asynccontextmanager

from app.config import database_url
from app.utils.logging import get_logger

logger = get_logger(__name__)

engine = create_async_engine(url=database_url)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession)
str_uniq = Annotated[str, mapped_column(unique=True, nullable=False)]


@asynccontextmanager
async def get_session():
    """Асинхронный контекстный менеджер для управления сессиями базы данных."""
    logger.debug("Создание новой сессии базы данных")
    session = async_session_maker()
    try:
        yield session
    except Exception as e:
        logger.error(f"Ошибка в сессии базы данных: {str(e)}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()
        logger.debug("Сессия базы данных закрыта")


def connection(isolation_level=None):
    def decorator(method):
        @wraps(method)
        async def wrapper(*args, **kwargs):
            # Извлекаем manager из kwargs, если он есть
            manager = kwargs.get("manager")

            async with async_session_maker() as session:
                try:
                    # Устанавливаем уровень изоляции, если передан
                    if isolation_level:
                        await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))

                    # Если есть manager, добавляем сессию в middleware_data
                    if manager and hasattr(manager, "middleware_data"):
                        manager.middleware_data["session"] = session

                    # Добавляем сессию в kwargs, если её там нет
                    if "session" not in kwargs:
                        kwargs["session"] = session

                    # Выполняем декорированный метод
                    result = await method(*args, **kwargs)
                    await session.commit()
                    return result
                except Exception as e:
                    await session.rollback()  # Откатываем сессию при ошибке
                    raise e  # Поднимаем исключение дальше
                finally:
                    if manager and hasattr(manager, "middleware_data") and "session" in manager.middleware_data:
                        del manager.middleware_data["session"]
                    await session.close()  # Закрываем сессию

        return wrapper

    return decorator


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'

    def to_dict(self, exclude_none: bool = False):
        """
        Преобразует объект модели в словарь.

        Args:
            exclude_none (bool): Исключать ли None значения из результата

        Returns:
            dict: Словарь с данными объекта
        """
        result = {}
        for column in inspect(self.__class__).columns:
            value = getattr(self, column.key)

            # Преобразование специальных типов данных
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            elif isinstance(value, uuid.UUID):
                value = str(value)

            # Добавляем значение в результат
            if not exclude_none or value is not None:
                result[column.key] = value

        return result

    def __repr__(self) -> str:
        """Строковое представление объекта для удобства отладки."""
        return f"<{self.__class__.__name__}(id={self.id}, created_at={self.created_at}, updated_at={self.updated_at})>"
