from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from helpers.config import get_settings, Settings

settings: Settings = get_settings()


def get_database_url() -> str:
    """
    Build the PostgreSQL async connection URL using asyncpg.
    """
    user = settings.POSTGRES_USERNAME
    password = settings.POSTGRES_PASSWORD
    host = settings.POSTGRES_HOST
    port = settings.POSTGRES_PORT
    database = settings.POSTGRES_MAIN_DATABASE

    if not all([user, password, host, port, database]):
        raise RuntimeError("Postgres settings are not fully configured")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


# This is what you import in main/factory:
# from models.db.postgres.db_session import engine, AsyncSessionLocal
engine: AsyncEngine = create_async_engine(
    get_database_url(),
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI-friendly dependency if you want to inject sessions directly:

        async def endpoint(db: AsyncSession = Depends(get_session)):
            ...

    """
    async with AsyncSessionLocal() as session:
        yield session
