from pickletools import optimize
from typing import Optional, List, Tuple, Union, overload
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import InsertOne

from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk
from .Enum.DataBaseEnums import DataBaseEnums
from helpers.oid import to_object_id


class ChunkModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase) -> None:
        super().__init__(db_client)
        self.collection: AsyncIOMotorCollection = self.db_client[
            DataBaseEnums.COLLECTION_CHUNK_NAME.value
        ]

    @classmethod
    async def create_instance(cls, db_client: AsyncIOMotorDatabase) -> "ChunkModel":
        instance: ChunkModel = cls(db_client)
        await instance.init_collection()
        return instance

    async def init_collection(self) -> None:
        all_collection = await self.db_client.list_collection_names()
        if DataBaseEnums.COLLECTION_CHUNK_NAME.value not in all_collection:
            self.collection = self.db_client[DataBaseEnums.COLLECTION_CHUNK_NAME.value]
            indexes = DataChunk.get_indices()
            for index in indexes:
                await self.collection.create_index(
                    keys=index["key"], name=index["name"], unique=index["unique"]
                )

    async def create_chunk(self, chunk: DataChunk) -> DataChunk:
        doc = chunk.model_dump(by_alias=True, exclude_none=True, mode="python")
        result = await self.collection.insert_one(doc)
        chunk.id = result.inserted_id
        return chunk

    async def get_chunk(self, chunk_id: Union[str, ObjectId]) -> Optional[DataChunk]:
        chunk_oid = to_object_id(chunk_id)
        if chunk_oid is None:
            return None
        doc = await self.collection.find_one({"_id": chunk_oid})
        return DataChunk.model_validate(doc) if doc else None

    async def insert_many_chunks(
        self, chunks: List[DataChunk], batch_size: int = 10
    ) -> Optional[int]:
        if not chunks:
            return None

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            operations = [
                InsertOne(chunk.model_dump(by_alias=True, exclude_none=True)) for chunk in batch
            ]
            await self.collection.bulk_write(operations)
        return len(chunks)

    async def list_by_project(
        self, project_id: Union[str, ObjectId], page: int = 1, page_size: int = 20
    ) -> Optional[Tuple[List[DataChunk], int]]:
        project_oid = to_object_id(project_id)
        if project_oid is None:
            return None
        filter_q = {"chunk_project_id": project_oid}
        total = await self.collection.count_documents(filter_q)
        total_pages = (total + page_size - 1) // page_size

        cursor = (
            self.collection.find(filter_q)
            .sort("chunk_order", 1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )

        items: List[DataChunk] = []
        async for doc in cursor:
            items.append(DataChunk.model_validate(doc))
        return items, total_pages

    async def delete_chunk(self, chunk_id: Union[str, ObjectId]) -> Optional[bool]:
        chunk_oid = to_object_id(chunk_id)
        if chunk_oid is None:
            return None
        res = await self.collection.delete_one({"_id": chunk_oid})
        return res.deleted_count == 1

    async def delete_chunks_by_project_id(
        self, chunk_project_id: Union[str, ObjectId]
    ) -> Optional[int]:
        chunk_project_oid = to_object_id(chunk_project_id)
        if chunk_project_oid is None:
            return None
        res = await self.collection.delete_many({"chunk_project_id": chunk_project_oid})
        return res.deleted_count or 0
