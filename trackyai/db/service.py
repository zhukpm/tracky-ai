import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from trackyai.config import settings
from trackyai.db.model import Base

logger = logging.getLogger(__name__)


class DbService:
    def __init__(self, engine: AsyncEngine):
        self.session_maker = async_sessionmaker(bind=engine, class_=AsyncSession)


# class EnvConfigService(DbService):
#     async def get(self) -> list[EnvironmentConfiguration]:
#         async with self.session_maker() as session:
#             # stmt = select


class ServiceManager:
    def __init__(self):
        self._engine: AsyncEngine = create_async_engine(
            url=settings.db_uri, echo='debug' if settings.debug_mode else False, logging_name='trackyai.db.engine'
        )

    async def recreate_database(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            await self._engine.dispose()
            logger.info('Database and tables created.')
