# src/models/db/factory.py
from typing import Any, Dict
from helpers.config import get_settings, Settings
from motor.motor_asyncio import AsyncIOMotorClient  # for Mongo
from .db_session import engine, AsyncSessionLocal


async def init_db_backend() -> Dict[str, Any]:
    settings: Settings = get_settings()
    backend = settings.DB_BACKEND.lower()

    # ----- MongoDB -----
    if backend == "mongodb":
        mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = mongo_client[settings.MONGODB_DATABASE]

        async def shutdown() -> None:
            mongo_client.close()

        return {
            "db_backend": "mongodb",
            "db_client": mongo_client,
            "db": db,
            "shutdown": shutdown,
        }

    # ----- PostgreSQL -----
    elif backend == "postgres":

        async def shutdown() -> None:
            await engine.dispose()

        return {
            "db_backend": "postgres",
            "db_client": engine,
            "db": AsyncSessionLocal,
            "shutdown": shutdown,
        }

    else:
        raise RuntimeError(f"Unsupported DB_BACKEND: {settings.DB_BACKEND}")
