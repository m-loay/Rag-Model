import uuid
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.sql import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import PgVectorTableSchemeEnums, DistanceMethodEnums
from models.db import RetrivedfDocument
import logging


class PgVectorProvider(VectorDBInterface):
    def __init__(
        self,
        db_client: async_sessionmaker[AsyncSession],
        distance_method: Optional[str],
        default_vector_size: int = 786,
    ) -> None:
        self.db_client = db_client
        self.distance_method = "<=>"
        if distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = "<->"
        self.default_vector_size = default_vector_size
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
            list_tbl = sql_text("SELECT 1 FROM pg_tables WHERE tablename = :collection_name")
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
            # 1) Query pg_tables for this table
            table_info_sql = sql_text(
                "SELECT schemaname, tablename, tableowner, tablespace, hasindexes "
                "FROM pg_tables "
                "WHERE tablename = :collection_name"
            )

            table_info_results = await session.execute(
                table_info_sql,
                {"collection_name": collection_name},
            )
            rows = table_info_results.fetchall()

            # 2) If there is no such table, return None (let controller handle it)
            if not rows:
                self.logger.error(f"pgvector table '{collection_name}' does not exist")
                return None

            # 3) Table exists -> count records
            count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')
            try:
                record_count_result = await session.execute(count_sql)
                record_count = record_count_result.scalar_one_or_none()
            except Exception as e:
                self.logger.error(f"Error counting rows in pgvector table '{collection_name}': {e}")
                record_count = None

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
            return True

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
            record_id = str(uuid.uuid4())

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
                    "chunk_id": int(record_id) if record_id is not None else None,
                },
            )
            await session.commit()
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
        if len(vectors) != n:
            self.logger.error(f"Length mismatch: texts({n}) vs vectors({len(vectors)})")
            return False

        if metadata is not None and len(metadata) != n:
            self.logger.error(f"Length mismatch: texts({n}) vs metadata({len(metadata)})")
            return False

        # record_ids are optional; if not provided, generate random ones
        if record_ids is not None and len(record_ids) != n:
            self.logger.error(f"Length mismatch: texts({n}) vs record_ids({len(record_ids)})")
            return False

        meta: List[Dict[str, Any]] = metadata if metadata is not None else [{} for _ in range(n)]

        ids: List[str] = (
            record_ids if record_ids is not None else [str(uuid.uuid4()) for _ in range(n)]
        )

        async with self.db_client() as session:
            for i in range(0, len(texts), batch_size):
                batch_end = i + batch_size
                batch_text = texts[i:batch_end]
                batch_vector = vectors[i:batch_end]
                batch_metadata = meta[i:batch_end]
                batch_record_ids = ids[i:batch_end]
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
                    f'INSERT INTO "{collection_name}" '
                    f"({PgVectorTableSchemeEnums.TEXT.value}, "
                    f"{PgVectorTableSchemeEnums.VECTOR.value}, "
                    f"{PgVectorTableSchemeEnums.METADATA.value}, "
                    f"{PgVectorTableSchemeEnums.CHUNK_ID.value}) "
                    "VALUES(:text, :vector, :metadata, :chunk_id)"
                )
                await session.execute(batch_insert_sql, batch_records)
                await session.commit()
        return True

    async def search_by_vector(
        self, collection_name: str, vector: List[float], limit: int = 5
    ) -> Optional[List[RetrivedfDocument]]:
        if not await self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist")
            return None

        async with self.db_client() as session:
            search_sql = sql_text(
                f"SELECT {PgVectorTableSchemeEnums.TEXT.value} as text, "
                f"({PgVectorTableSchemeEnums.VECTOR.value} {self.distance_method} :vector) as score "
                f"FROM {collection_name} "
                "ORDER BY score ASC "
                "LIMIT :limit"
            )
            vector_as_string_list = self._vector_to_string_list(vector=vector)
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
