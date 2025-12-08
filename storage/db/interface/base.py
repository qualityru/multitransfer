import asyncio
from typing import Any, Iterable

from loguru import logger
from sqlalchemy import (ColumnExpressionArgument, and_, asc, desc, func,
                        select, text, update)
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import (InstrumentedAttribute, Query, joinedload,
                            selectinload)

from config import settings
from storage.db.models import Base


class BaseInterface:
    def __init__(self, db_url: str = None, session_=None):
        """
        Класс-интерфейс для работы с БД. Держит сессию и предоставляет методы для работы с БД.

        :param db_url: Путь к БД формата: "database+driver://name:password@host/db_name"
        self.base базовый класс моделей с которыми будете работать.
        """
        if not session_:
            if not db_url:
                raise ValueError(
                    "db_url is required for Class DBInterface if session_ is None"
                )
            self.engine = create_async_engine(
                db_url, pool_timeout=60, pool_size=900, max_overflow=100
            )
            self.async_ses = async_sessionmaker(
                bind=self.engine, class_=AsyncSession, expire_on_commit=False
            )
        else:
            self.async_ses = session_

        self.base = Base

    async def initial(self):
        """
        Метод иницилизирует соеденение с БД.
        :return:
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(self.base.metadata.create_all)

    async def _drop_all(self):
        """
        Метод для удаления всех таблиц текущей БД.
        :return:
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(self.base.metadata.drop_all)

    async def _del_has_rows(self, session: AsyncSession, rows_object):
        for rec in rows_object:
            await session.delete(rec)

    async def del_has_rows(self, rows_object):
        async with self.async_ses() as session:
            await self._del_has_rows(session, rows_object)
            await session.commit()

    async def _delete_rows(self, session: AsyncSession, model: Base, **filter_by):
        records = await session.execute(Query(model).filter_by(**filter_by))
        records = records.scalars().all()

        # Если результаты найдены пробуем удалить
        if not records:
            return False
        for record in records:
            await session.delete(record)
        return True

    async def delete_rows(self, model: Base, **filter_by):
        async with self.async_ses() as session:
            result = await self._delete_rows(session, model, **filter_by)
            await session.commit()
            return result

    async def _get_rows_count(
        self,
        session: AsyncSession,
        model: Base,
        filters: list = None,
        filter: ColumnExpressionArgument = None,
        **kwargs,
    ):
        """
        Метод принимает класс модели и параметры по которым фильтровать и отдает кол-во строк
        :param model: Класс модели
        :param kwargs: Поля и их значения
        :return:int
        """

        query = select(func.count()).select_from(model).filter_by(**kwargs)
        if filters:
            query = query.where(and_(*filters))
        if filter:
            query = query.where(filter.get("filter"))

        return await session.scalar(query)

    async def get_rows_count(
        self,
        model: Base,
        filters: list = None,
        filter: ColumnExpressionArgument = None,
        **kwargs,
    ):
        async with self.async_ses() as session:
            return await self._get_rows_count(session, model, filters, filter, **kwargs)

    async def _get_row(
        self,
        session: AsyncSession,
        model: Base,
        order_by="id",
        order_direction="asc",
        filter: dict = None,
        load_relations: tuple[InstrumentedAttribute] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        **kwargs,
    ):
        """
        Метод принимает класс модели и имена полей со значениями,
        и если такая строка есть в БД - возвращает ее.
        :param to_many: Флаг для возврата одного или нескольких значений
        :param model: Класс модели
        :param kwargs: Поля и их значения
        :param load_relations: Список связанных сущностей для загрузки (например, ['auctiones', 'images'])
        :return:
        """

        # Строим основной запрос с фильтрацией по полям из kwargs
        query = select(model).filter_by(**kwargs)

        # Добавление фильтрации, если передано
        if filter:
            query = query.filter(filter["filter"])

        # Добавление сортировки
        if order_by:
            query = query.order_by(
                asc(order_by) if order_direction == "asc" else desc(order_by)
            )

        # Загрузка связанных данных, если указаны
        if load_relations:
            for relation in load_relations:
                query = query.options(
                    joinedload(relation)
                )  # Используется joinedload для предварительной загрузки

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        # Выполнение запроса
        result = await session.execute(query)

        return (
            result.scalars().first()
        )  # Возвращаем первый элемент или None, если не найдено

    async def get_row(
        self,
        model: Base,
        order_by="id",
        order_direction="asc",
        filter: dict = None,
        load_relations: tuple[InstrumentedAttribute] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        **kwargs,
    ):
        async with self.async_ses() as session:
            return await self._get_row(
                session,
                model,
                order_by,
                order_direction,
                filter,
                load_relations,
                offset,
                limit,
                **kwargs,
            )

    async def get_rows(
        self,
        model: Base | tuple[InstrumentedAttribute],
        order_by="id",
        order_direction="asc",
        filter: ColumnExpressionArgument = None,
        load_relations: tuple[InstrumentedAttribute] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        session: AsyncSession | None = None,
        **kwargs,
    ):
        if isinstance(filter, dict):
            filter = filter.get("filter")
        async with session if session else self.async_ses() as session:
            # Строим основной запрос с фильтрацией по полям из kwargs
            if isinstance(model, tuple):
                query = select(*model).filter_by(**kwargs)
            else:
                query = select(model).filter_by(**kwargs)

            # Добавление фильтрации, если передано
            if filter is not None:
                query = query.where(filter)

            # Добавление сортировки
            if order_by:
                if isinstance(order_by, list):
                    query = query.order_by(*order_by)
                else:
                    query = query.order_by(
                        asc(order_by) if order_direction == "asc" else desc(order_by)
                    )

            # Загрузка связанных данных, если указаны
            if load_relations:
                for relation in load_relations:
                    if isinstance(relation, tuple):
                        relation_chain = relation
                        loader = selectinload(relation_chain[0])
                        current = loader
                        for rel in relation_chain[1:]:
                            current = current.selectinload(rel)
                        query = query.options(loader)
                    else:
                        query = query.options(selectinload(relation))

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            # Выполнение запроса
            result = await session.execute(query)

            return (
                result.scalars().all()
                if not isinstance(model, Iterable)
                else result.mappings().all()
            )

    async def get_or_create_row(self, model: Any, filter_by=None, **kwargs):
        """
        Метод находит в БД запись, и возвращает ее. Если записи нет - создает и возвращает.
        :param model: Класс модели
        :param filter_by: Параметры для поиска записи. По умолчанию поиск идет по **kwargs
        :param kwargs: Поля и их значения
        :return:
        """
        if not filter_by:
            filter_by = kwargs

        async with self.async_ses() as session:
            row = await session.execute(Query(model).filter_by(**filter_by))
            res = row.scalar()
            if res is None:
                res = model(**kwargs)
                session.add(res)
                try:
                    await session.commit()
                    await session.refresh(res)
                except Exception as ex:
                    logger.warning(f"COMMIT FAILED: {model.__name__}, {kwargs=} {ex}")
            return res

    async def update_rows(
        self,
        model: Base,
        filter_by: dict,
        session: AsyncSession | None = None,
        **kwargs,
    ):
        async with session if session else self.async_ses() as session:
            row = await session.execute(
                update(model).filter_by(**filter_by).values(**kwargs).returning(model)
            )

            try:
                await session.commit()
                return row.scalar_one()
            except Exception as ex:
                print(f"failed update {model.__tablename__}")
                raise ex

    async def add_row(self, model: Base, **kwargs) -> Base:
        """
        Метод принимает класс модели и поля со значениями,
        и создает в таблице данной модели запись с переданными аргументами.
        :param model: Класс модели
        :param kwargs: Поля и их значения
        :return:
        """

        async with self.async_ses() as session:
            row = model(**kwargs)
            session.add(row)
            try:
                await session.commit()
                return row
            except Exception as ex:
                logger.warning(f"FAILED ADD ROW, {model.__name__}, {kwargs=}")
                raise ex

    async def get_row_num(
        self,
        model_column: InstrumentedAttribute,
        model_column_value: Any,
        where_=None,
        desc_=False,
    ) -> int | None:
        order_by_func = asc if not desc_ else desc

        subquery = select(
            model_column,
            func.row_number()
            .over(order_by=order_by_func(model_column))
            .label("row_num"),
        )

        if where_ is not None:
            subquery = subquery.where(where_)

        subquery = subquery.subquery()
        stmt = select(subquery.c.row_num).where(
            subquery.c[model_column.name] == model_column_value
        )
        async with self.async_ses() as session:
            try:
                result = await session.execute(stmt)
                return result.scalar()
            except Exception:
                logger.warning(f"FAILED ADD ROW, {model_column.__name__}")
                return

    async def truncate_table(self, model: Base):
        async with self.async_ses() as session:
            await session.execute(
                text(f"TRUNCATE TABLE {model.__tablename__} RESTART IDENTITY CASCADE")
            )
            await session.commit()

    async def add_rows(self, models: list[Base]) -> list[Base] | None:
        async with self.async_ses() as session:
            session.add_all(models)
            try:
                await session.flush()
                await session.commit()
                return models
            except Exception as ex:
                logger.warning("FAILED ADD ROWS")
                logger.exception(ex)
                return

    def get_subquery_filter(self, model, filter_by: dict, scalar_subquery=True):
        query = Query(model)
        if filter_by:
            query = query.filter_by(**filter_by)
        if scalar_subquery:
            query = query.limit(1).scalar_subquery()
        return query


async def main():
    db = BaseInterface(settings.DB_URL)
    await db.initial()


if __name__ == "__main__":
    asyncio.run(main())
