from contextlib import asynccontextmanager
from typing import cast
from fastapi import FastAPI, Request, Depends
from routes import base, data
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from helpers.config import get_settings, Settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings: Settings = get_settings()
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = mongo_client[settings.MONGODB_DATABASE]
    app.state.mongo_client = mongo_client
    app.state.db = db

    try:
        yield
    finally:
        # Shutdown
        mongo_client.close()

app = FastAPI(lifespan=lifespan)

def get_db(request: Request) -> AsyncIOMotorDatabase:
    return cast(AsyncIOMotorDatabase, request.app.state.db)

app.include_router(base.base_router, dependencies=[Depends(get_db)])
app.include_router(data.data_router, dependencies=[Depends(get_db)])