import asyncio

from trackyai.db.service import ServiceManager

service_manager = ServiceManager()


if __name__ == '__main__':
    asyncio.run(service_manager.recreate_database())
