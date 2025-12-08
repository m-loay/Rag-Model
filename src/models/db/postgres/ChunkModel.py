from sqlalchemy import func, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from typing import Sequence, Tuple, Optional, List, Union


from .BaseDataModel import BaseDataModel
from .db_schema.DataChunk import DataChunk


class ChunkModel(BaseDataModel):
    def __init__(self, db_client: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: async_sessionmaker[AsyncSession]) -> "ChunkModel":
        return cls(db_client)

    @staticmethod
    def _normalize_pk(value: Union[int, str]) -> int:
        return int(value)

    async def create_chunk(self, chunk: DataChunk) -> DataChunk:
        async with self.session_factory() as session:
            session.add(chunk)
            await session.commit()
            await session.refresh(chunk)
            return chunk

    async def get_chunk(self, chunk_id: Union[int, str]) -> Optional[DataChunk]:
        chunk_pk = self._normalize_pk(chunk_id)
        async with self.session_factory() as session:
            query = select(DataChunk).where(DataChunk.id == chunk_pk)
            result = await session.execute(query)
            chunk: Optional[DataChunk] = result.scalar_one_or_none()
        return chunk

    async def insert_many_chunks(
        self, chunks: List[DataChunk], batch_size: int = 100
    ) -> Optional[int]:
        if not chunks:
            return None
        async with self.session_factory() as session:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                session.add_all(batch)
                await session.flush()
            await session.commit()
        return len(chunks)

    async def get_project_chunks(
        self, project_id: Union[int, str], page: int = 1, page_size: int = 20
    ) -> Optional[Tuple[List[DataChunk], int]]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        project_pk = self._normalize_pk(project_id)
        async with self.session_factory() as session:
            query_count = select(func.count(DataChunk.id)).where(
                DataChunk.chunk_project_id == project_pk
            )
            results = await session.execute(query_count)
            total_chunks: int = results.scalar_one()
            if total_chunks == 0:
                return [], 0

            total_pages = (total_chunks + page_size - 1) // page_size

            stmt = (
                select(DataChunk)
                .where(DataChunk.chunk_project_id == project_pk)
                .order_by(DataChunk.chunk_order.asc(), DataChunk.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            records: List[DataChunk] = list(result.scalars().all())
        return records, total_pages

    async def delete_chunk(self, chunk_id: Union[int, str]) -> Optional[bool]:
        chunk_pk = self._normalize_pk(chunk_id)
        async with self.session_factory() as session:
            query = delete(DataChunk).where(DataChunk.id == chunk_pk)
            result = await session.execute(query)
            await session.commit()
        return result.rowcount == 1

    async def delete_chunks_by_project_id(self, chunk_project_id: Union[int, str]) -> Optional[int]:
        project_pk = self._normalize_pk(chunk_project_id)
        async with self.session_factory() as session:
            query = delete(DataChunk).where(DataChunk.chunk_project_id == project_pk)
            result = await session.execute(query)
            await session.commit()
        return result.rowcount or 0
