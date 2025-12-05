from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes import base, data, nlp
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings, Settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.llm.LLMInterface import LLMInterface
from stores.vectordb.VectorDBPoviderFactory import VectorDBPoviderFactory
from stores.vectordb.VectorDBInterface import VectorDBInterface
import logging

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------- STARTUP ----------
    settings: Settings = get_settings()

    # MongoDB client
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = mongo_client[settings.MONGODB_DATABASE]
    app.state.mongo_client = mongo_client
    app.state.db = db

    # LLM factory
    llm_provider_factory = LLMProviderFactory(config=settings)

    # vector db factory
    vectordb_provider_factory = VectorDBPoviderFactory(config=settings)

    # generation client
    generation_client: LLMInterface = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )
    generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
    app.state.generation_client = generation_client

    # embedding client
    embedding_client: LLMInterface = llm_provider_factory.create(
        provider=settings.EMBEDDING_BACKEND
    )
    embedding_client.set_embeddings_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )
    app.state.embedding_client = embedding_client

    # vector db client
    vectordb_client: VectorDBInterface = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )
    app.state.vectordb_client = vectordb_client
    app.state.vectordb_client.connect()

    # Yield control to the app (requests are handled here)
    yield
    app.state.mongo_client.close()
    app.state.vectordb_client.disconnect()


app = FastAPI(lifespan=lifespan)


app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
