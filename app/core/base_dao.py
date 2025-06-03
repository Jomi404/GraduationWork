from typing import List, TypeVar, Generic, Type, Optional, Union, Any, Sequence
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete, func, Row, RowMapping
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from .database import Base
from asyncpg.exceptions import ConnectionDoesNotExistError

T = TypeVar("T", bound=Base)


class BaseDAO(Generic[T]):
    model: Type[T] = None

    def __init__(self, session: AsyncSession):
        self._session = session
        if self.model is None:
            raise ValueError("Модель должна быть указана в дочернем классе")

    async def find_one_or_none_by_id(self, data_id: int):
        try:
            query = select(self.model).filter_by(id=data_id)
            result = await self._session.execute(query)
            record = result.scalar_one_or_none()
            logger.info(f"Запись {self.model.__name__} с ID {data_id} {'найдена' if record else 'не найдена'}.")
            return record
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при поиске записи с ID {data_id}: {e}")
            await self._session.rollback()
            raise

    async def find_one_or_none(self, filters: Union[BaseModel, dict], options: list = None):
        filter_dict = {}
        if isinstance(filters, BaseModel):
            filter_dict = filters.model_dump(exclude_unset=True)
        elif isinstance(filters, dict):
            filter_dict = filters
        else:
            raise ValueError("Filters must be a Pydantic model or a dictionary")
        logger.info(f"Поиск одной записи {self.model.__name__} по фильтрам: {filter_dict}")
        try:
            query = select(self.model).filter_by(**filter_dict)
            if options:
                query = query.options(*options)
            result = await self._session.execute(query)
            record = result.scalar_one_or_none()
            logger.info(f"Запись {'найдена' if record else 'не найдена'} по фильтрам: {filter_dict}")
            return record
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при поиске записи по фильтрам {filter_dict}: {e}")
            await self._session.rollback()
            raise

    async def find_all(
            self,
            filters: Optional[Union[BaseModel, dict]] = None,
            order_by: Optional[Any] = None,
    ) -> Sequence[Row[Any] | RowMapping | Any]:
        filter_dict = {}
        if filters:
            if isinstance(filters, BaseModel):
                filter_dict = filters.model_dump(exclude_unset=True)
            elif isinstance(filters, dict):
                filter_dict = filters
            else:
                raise ValueError("Filters must be a Pydantic model or a dictionary")
        logger.info(f"Поиск всех записей {self.model.__name__} по фильтрам: {filter_dict}")
        try:
            query = select(self.model).filter_by(**filter_dict)
            if order_by is not None:
                query = query.order_by(order_by)
            result = await self._session.execute(query)
            records = result.scalars().all()
            logger.info(f"Найдено {len(records)} записей.")
            return records
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при поиске всех записей по фильтрам {filter_dict}: {e}")
            await self._session.rollback()
            raise

    async def add(self, values: BaseModel):
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(f"Добавление записи {self.model.__name__} с параметрами: {values_dict}")
        try:
            new_instance = self.model(**values_dict)
            self._session.add(new_instance)
            await self._session.flush()
            logger.info(f"Запись {self.model.__name__} успешно добавлена.")
            return new_instance
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при добавлении записи: {e}")
            await self._session.rollback()
            raise

    async def add_many(self, instances: List[BaseModel]):
        values_list = [item.model_dump(exclude_unset=True) for item in instances]
        logger.info(f"Добавление нескольких записей {self.model.__name__}. Количество: {len(values_list)}")
        try:
            new_instances = [self.model(**values) for values in values_list]
            self._session.add_all(new_instances)
            await self._session.flush()
            logger.info(f"Успешно добавлено {len(new_instances)} записей.")
            return new_instances
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при добавлении нескольких записей: {e}")
            await self._session.rollback()
            raise

    async def update(self, filters: Union[BaseModel, dict], values: BaseModel):
        filter_dict = {}
        if isinstance(filters, BaseModel):
            filter_dict = filters.model_dump(exclude_unset=True)
        elif isinstance(filters, dict):
            filter_dict = filters
        else:
            raise ValueError("Filters must be a Pydantic model or a dictionary")
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(f"Обновление записей по фильтру: {filter_dict} с параметрами: {values_dict}")
        try:
            query = (
                sqlalchemy_update(self.model)
                .where(*[getattr(self.model, k) == v for k, v in filter_dict.items()])
                .values(**values_dict)
                .execution_options(synchronize_session="fetch")
            )
            result = await self._session.execute(query)
            await self._session.flush()
            logger.info(f"Обновлено {result.rowcount} записей.")
            return result.rowcount
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при обновлении записей: {e}")
            await self._session.rollback()
            raise

    async def delete(self, filters: Union[BaseModel, dict]):
        if isinstance(filters, BaseModel):
            filter_dict = filters.model_dump(exclude_unset=True)
        elif isinstance(filters, dict):
            filter_dict = filters
        else:
            raise ValueError("Фильтры должны быть моделью Pydantic или словарем")
        logger.info(f"Удаление записей по фильтру: {filter_dict}")
        if not filter_dict:
            raise ValueError("Нужен хотя бы один фильтр для удаления.")
        try:
            query = sqlalchemy_delete(self.model).filter_by(**filter_dict)
            result = await self._session.execute(query)
            await self._session.flush()
            logger.info(f"Удалено {result.rowcount} записей.")
            return result.rowcount
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при удалении записей: {e}")
            await self._session.rollback()
            raise

    async def count(self, filters: BaseModel | None = None):
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.info(f"Подсчет количества записей по фильтру: {filter_dict}")
        try:
            query = select(func.count(self.model.id)).filter_by(**filter_dict)
            result = await self._session.execute(query)
            count = result.scalar()
            logger.info(f"Найдено {count} записей.")
            return count
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при подсчете записей: {e}")
            await self._session.rollback()
            raise

    async def bulk_update(self, records: List[BaseModel]):
        logger.info(f"Массовое обновление записей")
        try:
            updated_count = 0
            for record in records:
                record_dict = record.model_dump(exclude_unset=True)
                if 'id' not in record_dict:
                    continue
                update_data = {k: v for k, v in record_dict.items() if k != 'id'}
                stmt = (
                    sqlalchemy_update(self.model)
                    .filter_by(id=record_dict['id'])
                    .values(**update_data)
                )
                result = await self._session.execute(stmt)
                updated_count += result.rowcount
            await self._session.flush()
            logger.info(f"Обновлено {updated_count} записей")
            return updated_count
        except (SQLAlchemyError, ConnectionDoesNotExistError) as e:
            logger.error(f"Ошибка при массовом обновлении: {e}")
            await self._session.rollback()
            raise
