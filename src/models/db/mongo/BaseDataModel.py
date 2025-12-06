from helpers.config import get_settings, Settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Final


class BaseDataModel:
    def __init__(self, db_client: AsyncIOMotorDatabase) -> None:
        self.db_client: Final[AsyncIOMotorDatabase] = db_client
        self.app_settings: Settings = get_settings()
