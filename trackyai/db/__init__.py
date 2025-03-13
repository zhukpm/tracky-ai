import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine

from trackyai.config import settings
from trackyai.db.model import Base

logger = logging.getLogger(__name__)


async def _create_database():
    engine = create_async_engine(settings.db_uri, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
        logger.info('Database and tables created.')


if __name__ == '__main__':
    asyncio.run(_create_database())
