from datetime import UTC, datetime
from functools import partial

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class EnvironmentConfiguration(Base):
    __tablename__ = 'env_config'

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    description = Column(Text, nullable=False)


class Expense(Base):
    __tablename__ = 'expense'

    __table_args__ = (CheckConstraint('amount >= 0', name='check_amount_non_negative'),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    date = Column(DateTime, nullable=False, default=partial(datetime.now, tz=UTC))
    currency = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    comment = Column(Text, nullable=False, default='')

    # Relationships
    category = relationship('Category', back_populates='expenses')


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=False)

    # Relationships
    expenses = relationship('Expense', back_populates='category')


class Memory(Base):
    __tablename__ = 'memory'

    user_id = Column(Integer, primary_key=True, autoincrement=False)
    memory = Column(Text, nullable=False)
