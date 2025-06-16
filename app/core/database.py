import uuid
from functools import wraps
from typing import Annotated
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, TIMESTAMP, Integer, inspect, text
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, declared_attr
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession
from contextlib import asynccontextmanager
from asyncpg.exceptions import ConnectionDoesNotExistError
from sqlalchemy.exc import DBAPIError, PendingRollbackError

from app.config import database_url
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Создание асинхронного движка с улучшенной конфигурацией пула
engine = create_async_engine(
    url=database_url,
    pool_size=10,           # Максимальное количество соединений в пуле
    max_overflow=20,        # Дополнительные соединения при переполнении
    pool_timeout=30,        # Таймаут ожидания соединения
    pool_recycle=300,       # Обновление соединений каждые 5 минут
    pool_pre_ping=True      # Проверка соединений перед использованием
)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

str_uniq = Annotated[str, mapped_column(unique=True, nullable=False)]


@asynccontextmanager
async def get_session():
    """Асинхронный контекстный менеджер для управления сессиями базы данных."""
    logger.debug("Создание новой сессии базы данных")
    session = async_session_maker()
    try:
        yield session
        await session.commit()
    except (ConnectionDoesNotExistError, DBAPIError, PendingRollbackError) as e:
        logger.error(f"Ошибка соединения с базой данных: {str(e)}", exc_info=True)
        try:
            await session.rollback()
        except Exception as rollback_err:
            logger.error(f"Ошибка при откате транзакции: {str(rollback_err)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Ошибка в сессии базы данных: {str(e)}", exc_info=True)
        await session.rollback()
        raise
    finally:
        try:
            await session.close()
            logger.debug("Сессия базы данных закрыта")
        except Exception as close_err:
            logger.error(f"Ошибка при закрытии сессии: {str(close_err)}", exc_info=True)


def connection(isolation_level=None):
    def decorator(method):
        @wraps(method)
        async def wrapper(*args, **kwargs):
            async with get_session() as session:
                try:
                    if isolation_level:
                        await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))

                    manager = kwargs.get("manager")
                    if manager and hasattr(manager, "middleware_data"):
                        manager.middleware_data["session"] = session

                    if "session" not in kwargs:
                        kwargs["session"] = session

                    result = await method(*args, **kwargs)
                    return result
                except (ConnectionDoesNotExistError, DBAPIError, PendingRollbackError) as e:
                    logger.error(f"Ошибка в транзакции: {str(e)}", exc_info=True)
                    try:
                        await session.rollback()
                    except Exception as rollback_err:
                        logger.error(f"Ошибка при откате транзакции: {str(rollback_err)}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Ошибка в методе {method.__name__}: {str(e)}", exc_info=True)
                    await session.rollback()
                    raise
                finally:
                    if manager and hasattr(manager, "middleware_data") and "session" in manager.middleware_data:
                        del manager.middleware_data["session"]

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
        result = {}
        for column in inspect(self.__class__).columns:
            value = getattr(self, column.key)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            elif isinstance(value, uuid.UUID):
                value = str(value)
            if not exclude_none or value is not None:
                result[column.key] = value
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, created_at={self.created_at}, updated_at={self.updated_at})>"
