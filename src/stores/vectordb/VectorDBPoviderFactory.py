from pathlib import Path
from typing import Optional
from .providers import QuadrantDBProvider
from helpers.config import Settings
from .VectorDBEnums import VectorDBEnums
from .VectorDBInterface import VectorDBInterface
from controllers.DBController import DBController


class VectorDBPoviderFactory:
    def __init__(self, config: Settings) -> None:
        self.config: Settings = config
        self.db_controller: DBController = DBController()

    def create(self, provider: str) -> VectorDBInterface:
        db_path: Path = self.db_controller.get_db_path(db_name=self.config.VECTOR_DB_PATH)
        if provider == VectorDBEnums.QDRANT.value:
            return QuadrantDBProvider(
                db_path=db_path, distance_method=self.config.VECTOR_DB_DISTANCE_METHOD
            )
        else:
            raise ValueError(f"{provider} is not supported")
