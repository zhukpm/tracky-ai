import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = ['Base', 'EnvironmentConfiguration', 'Expense', 'Category', 'Memory']


class Base(AsyncAttrs, DeclarativeBase):
    pass


class EnvironmentConfiguration(Base):
    __tablename__ = 'env_config'

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]
    description: Mapped[str] = mapped_column(Text)


class Expense(Base):
    __tablename__ = 'expense'

    __table_args__ = (CheckConstraint('amount >= 0', name='check_amount_non_negative'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('category.id'))
    date: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    currency: Mapped[str]
    amount: Mapped[float]
    comment: Mapped[str] = mapped_column(Text, default='')

    # Relationships
    category: Mapped['Category'] = relationship('Category', back_populates='expenses')


class Category(Base):
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str] = mapped_column(Text)

    # Relationships
    expenses: Mapped[list[Expense]] = relationship('Expense', back_populates='category')


class Memory(Base):
    __tablename__ = 'memory'

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    memory: Mapped[str] = mapped_column(Text)
