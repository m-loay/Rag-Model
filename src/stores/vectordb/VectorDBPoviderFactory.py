from pathlib import Path
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from .providers import QuadrantDBProvider, PgVectorProvider
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

        if provider == VectorDBEnums.PGVECTOR.value:
            user = self.config.POSTGRES_USERNAME
            password = self.config.POSTGRES_PASSWORD
            host = self.config.POSTGRES_HOST
            port = self.config.POSTGRES_PORT
            database = self.config.POSTGRES_MAIN_DATABASE
            url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
            engine = create_async_engine(url, echo=False, future=True)
            session_factory = async_sessionmaker(
                bind=engine, expire_on_commit=False, class_=AsyncSession
            )
            return PgVectorProvider(
                db_client=session_factory,
                default_vector_size=self.config.EMBEDDING_MODEL_SIZE,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHOD,
            )
        raise ValueError(f"{provider} is not supported")
