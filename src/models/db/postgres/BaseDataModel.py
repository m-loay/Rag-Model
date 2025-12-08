from typing import Final
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from helpers.config import get_settings, Settings


class BaseDataModel:
    def __init__(self, db_client: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory: Final[async_sessionmaker[AsyncSession]] = db_client
        self.app_settings: Settings = get_settings()
