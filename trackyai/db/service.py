import datetime
import logging
from typing import Sequence, cast

from sqlalchemy import ColumnElement, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import joinedload

from trackyai.config import settings
from trackyai.db.model import Base, Category, EnvironmentConfiguration, Expense, Memory

logger = logging.getLogger(__name__)


class DbService:
    def __init__(self, engine: AsyncEngine):
        self.session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


class EnvConfigService(DbService):
    async def get(self, key: str) -> EnvironmentConfiguration:
        stmt = select(EnvironmentConfiguration).where(cast(ColumnElement[bool], EnvironmentConfiguration.key == key))
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).one()

    async def get_all(self) -> Sequence[EnvironmentConfiguration]:
        stmt = select(EnvironmentConfiguration)
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).all()

    async def update(self, key: str, value: str) -> EnvironmentConfiguration:
        async with self.session_maker() as session, session.begin():
            ec: EnvironmentConfiguration = (
                await session.scalars(
                    select(EnvironmentConfiguration).where(
                        cast(ColumnElement[bool], EnvironmentConfiguration.key == key)
                    )
                )
            ).one()
            ec.value = value
            return ec


class MemoryService(DbService):
    async def get(self, user_id: int) -> Memory:
        stmt = select(Memory).where(cast(ColumnElement[bool], Memory.user_id == user_id))
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).one()

    async def update(self, user_id: int, memory: str) -> Memory:
        async with self.session_maker() as session, session.begin():
            mem: Memory = (
                await session.scalars(select(Memory).where(cast(ColumnElement[bool], Memory.user_id == user_id)))
            ).one()
            mem.memory = memory
            return mem


class CategoryService(DbService):
    async def get(self, category_id: int) -> Category:
        stmt = select(Category).where(cast(ColumnElement[bool], Category.id == category_id))
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).one()

    async def get_all(self) -> Sequence[Category]:
        stmt = select(Category)
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).all()

    async def add(self, name: str, description: str) -> Category:
        category = Category(name=name, description=description)
        async with self.session_maker() as session, session.begin():
            session.add(category)
            return category

    async def update(self, category_id: int, name: str | None = None, description: str | None = None) -> Category:
        if name is None and description is None:
            raise ValueError('Either name or description must be specified to update a category')
        async with self.session_maker() as session, session.begin():
            try:
                category: Category = (
                    await session.scalars(select(Category).where(cast(ColumnElement[bool], Category.id == category_id)))
                ).one()
            except NoResultFound:
                raise ValueError(f'Category with id {category_id} does not exist') from None
            if name is not None:
                category.name = name
            if description is not None:
                category.description = description
            return category


class ExpenseService(DbService):
    async def get(self, expense_id: int) -> Expense:
        stmt = (
            select(Expense)
            .where(cast(ColumnElement[bool], Expense.id == expense_id))
            .options(joinedload(Expense.category, innerjoin=True))
        )
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).one()

    async def get_many(self, expense_ids: list[int]) -> Sequence[Expense]:
        stmt = (
            select(Expense)
            .where(cast(ColumnElement[bool], Expense.id.in_(expense_ids)))
            .options(joinedload(Expense.category, innerjoin=True))
        )
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).all()

    async def get_all(self) -> Sequence[Expense]:
        stmt = select(Expense).options(joinedload(Expense.category, innerjoin=True))
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).all()

    async def add(self, category_id: int, currency: str, amount: float, comment: str | None = None) -> Expense:
        async with self.session_maker() as session, session.begin():
            try:
                category = (
                    await session.scalars(select(Category).where(cast(ColumnElement[bool], Category.id == category_id)))
                ).one()
            except NoResultFound:
                raise ValueError(f'Category with id {category_id} does not exist') from None
            expense = Expense(currency=currency, amount=amount, comment=comment or '', category=category)
            session.add(expense)
            return expense

    async def update(
        self,
        expense_id: int,
        category_id: int | None = None,
        date: datetime.datetime | None = None,
        currency: str | None = None,
        amount: float | None = None,
        comment: str | None = None,
    ) -> Expense:
        if not any(map(lambda x: x is not None, (category_id, date, currency, amount, comment))):
            raise ValueError('At least one value must be specified to update an expense')
        async with self.session_maker() as session, session.begin():
            try:
                expense = (
                    await session.scalars(
                        select(Expense)
                        .where(cast(ColumnElement[bool], Expense.id == expense_id))
                        .options(joinedload(Expense.category, innerjoin=True))
                    )
                ).one()
            except NoResultFound:
                raise ValueError(f'Expense with id {expense_id} does not exist') from None
            if category_id is not None:
                try:
                    category = (
                        await session.scalars(
                            select(Category).where(cast(ColumnElement[bool], Category.id == category_id))
                        )
                    ).one()
                except NoResultFound:
                    raise ValueError(f'Category with id {category_id} does not exist') from None
                expense.category = category
            if date is not None:
                expense.date = date
            if currency is not None:
                expense.currency = currency
            if amount is not None:
                expense.amount = amount
            if comment is not None:
                expense.comment = comment
            return expense

    async def find(
        self,
        category_id: int | None = None,
        date_from: datetime.datetime | None = None,
        date_to: datetime.datetime | None = None,
        currency: str | list[str] | None = None,
        amount_from: float | None = None,
        amount_to: float | None = None,
        comment_like: str | None = None,
        limit: int | None = None,
    ) -> Sequence[Expense]:
        conditions = []
        if category_id is not None:
            conditions.append(Expense.category_id == category_id)
        if date_from is not None:
            conditions.append(Expense.date >= date_from)
        if date_to is not None:
            conditions.append(Expense.date <= date_to)
        if currency is not None:
            if isinstance(currency, str):
                currency = [currency]
            conditions.append(Expense.currency.in_(currency))
        if amount_from is not None:
            conditions.append(Expense.amount >= amount_from)
        if amount_to is not None:
            conditions.append(Expense.amount <= amount_to)
        if comment_like is not None:
            if not comment_like.startswith('%'):
                comment_like = '%' + comment_like
            if not comment_like.endswith('%'):
                comment_like += '%'
            conditions.append(Expense.comment.like(comment_like))
        stmt = (
            select(Expense)
            .where(*conditions)
            .options(joinedload(Expense.category, innerjoin=True))
            .order_by(Expense.date.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).all()

    async def latest(self, limit: int) -> Sequence[Expense]:
        stmt = (
            select(Expense)
            .options(joinedload(Expense.category, innerjoin=True))
            .order_by(Expense.date.desc())
            .limit(limit)
        )
        async with self.session_maker() as session:
            return (await session.scalars(stmt)).all()


class ServiceManager:
    def __init__(self):
        self._engine: AsyncEngine = create_async_engine(
            url=settings.db_uri, echo='debug' if settings.debug_mode else False, logging_name='trackyai.db.engine'
        )
        self.env_config = EnvConfigService(self._engine)
        self.category = CategoryService(self._engine)
        self.expense = ExpenseService(self._engine)
        self.memory = MemoryService(self._engine)

    async def create_database(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await self._engine.dispose()
            logger.info('Database and tables created.')

    async def drop_database(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info('Database tables dropped.')
