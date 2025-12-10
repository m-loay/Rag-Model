import uuid
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.sql import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import (
    PgVectorDistanceMethodEnums,
    PgVectorIndexTypeEnums,
    PgVectorTableSchemeEnums,
    DistanceMethodEnums,
)
from models.db import RetrivedfDocument
import logging


class PgVectorProvider(VectorDBInterface):
    def __init__(
        self,
        db_client: async_sessionmaker[AsyncSession],
        distance_method: Optional[str],
        default_vector_size: int = 786,
        index_threshold: int = 100,
    ) -> None:
        self.db_client = db_client
        if distance_method == DistanceMethodEnums.COSINE.value:
            distance_method = PgVectorDistanceMethodEnums.COSINE.value
        elif distance_method == DistanceMethodEnums.DOT.value:
            distance_method = PgVectorDistanceMethodEnums.DOT.value
        self.distance_method = distance_method
        self.default_vector_size = default_vector_size
        self.index_threshold = index_threshold
        self.pgvector_table_prefix = PgVectorTableSchemeEnums._PREFIX.value

        self.logger = logging.getLogger(__name__)

    async def connect(self) -> None:
        async with self.db_client() as session:
            await session.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
            await session.commit()

    async def disconnect(self) -> None:
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:
        async with self.db_client() as session:
            list_tbl = sql_text(f"SELECT 1 FROM pg_tables WHERE tablename = :collection_name")
            results = await session.execute(list_tbl, {"collection_name": collection_name})
            record = results.scalar_one_or_none()
        if record is None:
            return False
        return True

    async def list_all_collections(self) -> Optional[List[str]]:
        async with self.db_client() as session:
            list_tbl = sql_text("SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix")
            results = await session.execute(list_tbl, {"prefix": f"{self.pgvector_table_prefix}%"})
            record_one_fetch = results.fetchone()
            if record_one_fetch is None:
                return None
        return list(results.scalars().all())

    async def get_collect_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        async with self.db_client() as session:
            # 1. Query pg_tables for this table
            table_info_sql = sql_text(
                "SELECT schemaname, tablename, tableowner, tablespace, hasindexes "
                "FROM pg_tables "
                f"WHERE tablename = :collection_name"
            )
            table_info_results = await session.execute(
                table_info_sql, {"collection_name": collection_name}
            )
            rows = table_info_results.fetchall()
            if not rows:
                self.logger.error(f"pgvector table '{collection_name}' does not exist")
                return None

            # 2. Table exists -> count records
            count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')
            record_count_result = await session.execute(count_sql)
            record_count = record_count_result.scalar_one_or_none()
            if not record_count:
                self.logger.error(f"pgvector table '{collection_name}' could not be count")
                return None

            return {
                "table_info": [dict(row._mapping) for row in rows],
                "record_count": record_count,
            }

    async def delete_collection(self, collection_name: str) -> bool:
        if not await self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist")
            return False

        async with self.db_client() as session:
            delete_sql = sql_text(f'DROP TABLE IF EXISTS "{collection_name}"')
            await session.execute(delete_sql)
            await session.commit()
        return True

    async def create_collection(
        self, collection_name: str, embedding_size: int, do_reset: bool
    ) -> bool:
        if do_reset:
            _ = await self.delete_collection(collection_name=collection_name)

        # If it already exists (and we didn't reset), just keep it
        if await self.is_collection_existed(collection_name=collection_name):
            self.logger.info(f"Collection/table {collection_name} already exists")
            return False

        # Only here do we actually CREATE TABLE
        self.logger.info(f"creating collection/table {collection_name}")
        async with self.db_client() as session:
            create_sql = sql_text(
                f'CREATE TABLE {collection_name} ('
                f'{PgVectorTableSchemeEnums.ID.value} bigserial PRIMARY KEY,'
                f'{PgVectorTableSchemeEnums.TEXT.value} text, '
                f'{PgVectorTableSchemeEnums.VECTOR.value} vector({embedding_size}), '
                f'{PgVectorTableSchemeEnums.METADATA.value} jsonb DEFAULT \'{{}}\', '
                f'{PgVectorTableSchemeEnums.CHUNK_ID.value} integer, '
                f'FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) '
                f'REFERENCES chunks(id) ON DELETE CASCADE'
                ')'
            )
            await session.execute(create_sql)
            await session.commit()
        return True

    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        record_id: Optional[str] = None,
    ) -> bool:
        if not await self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist")
            return False

        if record_id is None:
            self.logger.error(f"Can not insert new record without chunk_id: {collection_name}")
            return False

        async with self.db_client() as session:
            vector_as_string_list = self._vector_to_string_list(vector=vector)
            insert_sql = sql_text(
                f"INSERT INTO {collection_name} "
                f"({PgVectorTableSchemeEnums.TEXT.value}, "
                f"{PgVectorTableSchemeEnums.VECTOR.value}, "
                f"{PgVectorTableSchemeEnums.METADATA.value}, "
                f"{PgVectorTableSchemeEnums.CHUNK_ID.value}) "
                "VALUES (:text, :vector, :metadata, :chunk_id)"
            )
            await session.execute(
                insert_sql,
                {
                    "text": text,
                    "vector": vector_as_string_list,
                    "metadata": json.dumps(metadata or {}),
                    "chunk_id": int(record_id),
                },
            )
            await session.commit()
            await self._create_vector_index(collection_name=collection_name)
        return True

    async def insert_many(
        self,
        collection_name: str,
        texts: List[str],
        vectors: List[List[float]],
        metadata: Optional[List[Dict[str, Any]]] = None,
        record_ids: Optional[List[str]] = None,
        batch_size: int = 50,
    ) -> bool:
        if not await self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist")
            return False

        n = len(texts)
        if n == 0:
            self.logger.error("Cannot insert empty batch (texts list is empty)")
            return False

        if len(vectors) != n:
            self.logger.error(f"Length mismatch: texts({n}) vs vectors({len(vectors)})")
            return False

        if record_ids is None or len(record_ids) != n:
            self.logger.error(
                f"Length mismatch: texts({n}) vs record_ids({len(record_ids) if record_ids else None})"
            )
            return False

        if not metadata or len(metadata) != n:
            meta: List[Dict[str, Any]] = [{} for _ in range(n)]
        else:
            meta = metadata

        async with self.db_client() as session:
            for i in range(0, len(texts), batch_size):
                batch_end = i + batch_size
                batch_text = texts[i:batch_end]
                batch_vector = vectors[i:batch_end]
                batch_metadata = meta[i:batch_end]
                batch_record_ids = record_ids[i:batch_end]
                batch_records = [
                    {
                        "text": batch_text[j],
                        "vector": self._vector_to_string_list(batch_vector[j]),
                        "metadata": json.dumps(batch_metadata[j] or {}),
                        "chunk_id": int(batch_record_ids[j]),
                    }
                    for j in range(len(batch_text))
                ]
                batch_insert_sql = sql_text(
                    f"INSERT INTO {collection_name} "
                    f"({PgVectorTableSchemeEnums.TEXT.value}, "
                    f"{PgVectorTableSchemeEnums.VECTOR.value}, "
                    f"{PgVectorTableSchemeEnums.METADATA.value}, "
                    f"{PgVectorTableSchemeEnums.CHUNK_ID.value}) "
                    "VALUES(:text, :vector, :metadata, :chunk_id)"
                )
                await session.execute(batch_insert_sql, batch_records)
                await session.commit()
            await self._create_vector_index(collection_name=collection_name)
        return True

    async def search_by_vector(
        self, collection_name: str, vector: List[float], limit: int = 5
    ) -> Optional[List[RetrivedfDocument]]:
        if not await self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist")
            return None

        vector_as_string_list = self._vector_to_string_list(vector=vector)
        async with self.db_client() as session:
            search_sql = sql_text(
                f"SELECT {PgVectorTableSchemeEnums.TEXT.value} as text, "
                f"1 - ({PgVectorTableSchemeEnums.VECTOR.value} <=> :vector) as score "
                f"FROM {collection_name} "
                "ORDER BY score DESC "
                "LIMIT :limit"
            )

            result = await session.execute(
                search_sql,
                {"vector": vector_as_string_list, "limit": limit},
            )
            records = result.fetchall()
        if not records:
            return None
        results: List[RetrivedfDocument] = []
        for record in records:
            rec = RetrivedfDocument(
                text=str(record.text),
                score=float(record.score),
            )
            results.append(rec)
        return results

    def _vector_to_string_list(self, vector: List[float]) -> str:
        return "[" + ",".join([str(v) for v in vector]) + "]"

    def _get_pgvector_index_name(self, collection_name: str) -> str:
        return f"{collection_name}_vector_idx"

    async def _is_index_existed(self, collection_name: str) -> bool:
        index_name = self._get_pgvector_index_name(collection_name=collection_name)
        async with self.db_client() as session:
            check_sql = sql_text(
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = :collection_name "
                "AND indexname = :index_name"
            )
            results = await session.execute(
                check_sql,
                {
                    "collection_name": collection_name,
                    "index_name": index_name,
                },
            )
            return bool(results.scalar_one_or_none())

    async def _create_vector_index(
        self, collection_name: str, index_type: str = PgVectorIndexTypeEnums.HNSW.value
    ) -> bool:
        if await self._is_index_existed(collection_name=collection_name):
            return False
        async with self.db_client() as session:
            count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')
            result = await session.execute(count_sql)
            record_count = result.scalar_one()

            if record_count < self.index_threshold:
                return False

            self.logger.info(f"START: Creating vector Index for {collection_name}")
            index_name = self._get_pgvector_index_name(collection_name=collection_name)
            create_idx_sql = sql_text(
                f"CREATE INDEX {index_name} ON {collection_name} "
                f"USING {index_type} ({PgVectorTableSchemeEnums.VECTOR.value} {self.distance_method}) "
            )
            await session.execute(create_idx_sql)
            self.logger.info(f"END: Creating vector Index for {collection_name}")
        return True

    async def _reset_vector_index(
        self, collection_name: str, index_type: str = PgVectorIndexTypeEnums.HNSW.value
    ):
        index_name = self._get_pgvector_index_name(collection_name=collection_name)
        async with self.db_client() as session:
            drop_sql = sql_text(f"DROP INDEX IF EXISTS {index_name}")
            await session.execute(drop_sql)
        return self._create_vector_index(collection_name=collection_name, index_type=index_type)
