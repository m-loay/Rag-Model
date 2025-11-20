from typing import Optional, List, Dict, Any, cast
from pathlib import Path
import uuid
from qdrant_client import models, QdrantClient
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import VectorDBEnums, DistanceMethodEnums
import logging


class QuadrantDBProvider(VectorDBInterface):
    def __init__(self, db_path: Path, distance_method: Optional[str]) -> None:
        self.db_path: Path = db_path
        self.client: Optional[QdrantClient] = None

        self.distance_method = models.Distance.COSINE
        if distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT

        self.logger = logging.getLogger(__name__)

    def connect(self) -> None:
        self.client = QdrantClient(path=str(self.db_path))

    def disconnect(self) -> None:
        self.client = None

    def is_collection_existed(self, collection_name: str) -> bool:
        if self.client is None:
            self.logger.error("Qdrant client is not connected. Call connect() first")
            return False
        return self.client.collection_exists(collection_name=collection_name)

    def list_all_collections(self) -> Optional[List[str]]:
        if self.client is None:
            self.logger.error("Qdrant client is not connected. Call connect() first")
            return None
        response = self.client.get_collections()
        return [c.name for c in response.collections]

    def get_collect_info(self, collection_name: str) -> Optional[Dict]:
        if self.client is None:
            self.logger.error("Qdrant client is not connected. Call connect() first")
            return None
        info = self.client.get_collection(collection_name=collection_name)
        return cast(Dict, info)

    def delete_collection(self, collection_name: str) -> bool:
        if self.client is None:
            self.logger.error("Qdrant client is not connected. Call connect() first")
            return False
        if not self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"{collection_name} doesnt exist in DB")
            return False
        return self.client.delete_collection(collection_name=collection_name)

    def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool) -> bool:
        if self.client is None:
            self.logger.error("Qdrant client is not connected. Call connect() first")
            return False

        if do_reset:
            _ = self.delete_collection(collection_name=collection_name)

        return self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=embedding_size, distance=self.distance_method),
        )

    def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: List,
        metadta: Optional[Dict] = None,
        record_id: Optional[str] = None,
    ) -> bool:
        if self.client is None:
            self.logger.error("Qdrant client is not connected. Call connect() first")
            return False

        if not self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"{collection_name} is already existed")
            return False

        if record_id is None:
            record_id = str(uuid.uuid4())

        try:
            _ = self.client.upload_records(
                collection_name=collection_name,
                records=[
                    models.Record(
                        id=record_id, vector=vector, payload={"text": text, "metadata": metadta}
                    )
                ],
            )
        except Exception as e:
            self.logger.error(f"Error while inserting batch {e}")
        return True

    def insert_many(
        self,
        collection_name: str,
        texts: List[str],
        vectors: List[List[float]],
        metadta: Optional[List[Dict]] = None,
        record_ids: Optional[List[str]] = None,
        batch_size: int = 50,
    ) -> bool:
        if self.client is None:
            self.logger.error("Qdrant client is not connected. Call connect() first")
            return False

        if not self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist")
            return False

        n = len(texts)
        if len(vectors) != n:
            self.logger.error(f"Length mismatch: texts({n}) vs vectors({len(vectors)})")
            return False

        if metadta is not None and len(metadta) != n:
            self.logger.error(f"Length mismatch: texts({n}) vs metadta({len(metadta)})")
            return False

        if record_ids is not None and len(record_ids) != n:
            self.logger.error(f"Length mismatch: texts({n}) vs record_ids({len(record_ids)})")
            return False

        meta: List[Any] = metadta if metadta is not None else [None] * n

        ids: List[str] = (
            record_ids if record_ids is not None else [str(uuid.uuid4()) for _ in range(n)]
        )

        for i in range(0, len(texts), batch_size):
            batch_end = i + batch_size
            batch_text = texts[i:batch_end]
            batch_vector = vectors[i:batch_end]
            batch_metadata = meta[i:batch_end]
            batch_record_ids = ids[i:batch_end]

            batch_records = [
                models.Record(
                    id=batch_record_ids[j],
                    vector=batch_vector[j],
                    payload={"text": batch_text[j], "metadta": batch_metadata[j]},
                )
                for j in range(len(batch_text))
            ]
            try:
                _ = self.client.upload_records(
                    collection_name=collection_name, records=batch_records
                )
            except Exception as e:
                self.logger.error(f"Error while inserting batch {e}")

        return True

    def search_by_vector(
        self, collection_name: str, vector: List, limit: int = 5
    ) -> Optional[List[Any]]:
        if self.client is None:
            self.logger.error("Qdrant client is not connected. Call connect() first")
            return None
        return self.client.search(collection_name=collection_name, query_vector=vector, limit=limit)
