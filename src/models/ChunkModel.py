from typing import Optional, List, Tuple, Union, overload
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import InsertOne

from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk
from .Enum.DataBaseEnums import DataBaseEnums

@overload
def to_object_id(value: str) -> ObjectId: ...
@overload
def to_object_id(value: ObjectId) -> ObjectId: ...

def to_object_id(value: Union[str, ObjectId]) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(value)  # type: ignore[arg-type]  # (optional; most linters won't need this)
    except (InvalidId, TypeError) as e:
        raise ValueError("Invalid ObjectId") from e

class ChunkModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase) -> None:
        super().__init__(db_client)
        self.collection: AsyncIOMotorCollection = self.db_client[
            DataBaseEnums.COLLECTION_CHUNK_NAME.value
        ]

    async def create_chunk(self, chunk: DataChunk) -> DataChunk:
        doc = chunk.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(doc)
        chunk.id = result.inserted_id
        return chunk

    async def get_chunk(self, chunk_id: str) -> Optional[DataChunk]:
        doc = await self.collection.find_one({"_id": ObjectId(chunk_id)})
        if not doc:
            return None
        return DataChunk.model_validate(doc)
    
    async def insert_many_chunks(self, chunks: List[DataChunk], batch_size: int=10) -> int:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i: i+batch_size]
            operations = [InsertOne(chunk.model_dump(by_alias=True, exclude_none=True))
                         for chunk in batch]
            await self.collection.bulk_write(operations)
        return len(chunks)

    async def list_by_project(
        self, project_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[DataChunk], int]:
        """List chunks for a project with pagination."""
        filter_q = {"chunk_project_id": ObjectId(project_id)}
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

    async def delete_chunk(self, chunk_id: str) -> bool:
        res = await self.collection.delete_one({"_id": ObjectId(chunk_id)})
        return res.deleted_count == 1
    
    async def delete_chunks_by_project_id(self, project_ref: Union[str, ObjectId]) -> int:
        if project_ref is None:
            return 0
        if isinstance(project_ref, ObjectId):
            oid = project_ref
        else:
            try:
                oid = ObjectId(project_ref)
            except Exception:
                oid = None  # project_ref might be a human ID, not Mongo _id

        deleted = 0
        if oid is not None:
            res = await self.collection.delete_many({"chunk_project_id": str(oid)})
            deleted += res.deleted_count or 0
        return deleted

            
        