import asyncio

from trackyai.db.model import Category, EnvironmentConfiguration, Expense, Memory
from trackyai.db.service import ServiceManager

service_manager = ServiceManager()

__all__ = ['service_manager', 'Expense', 'Category', 'EnvironmentConfiguration', 'Memory']


if __name__ == '__main__':
    asyncio.run(service_manager.create_database())
