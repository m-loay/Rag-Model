from abc import ABC, abstractmethod
from models.db import RetrivedfDocument
from typing import Optional, Any, List, Dict


class VectorDBInterface(ABC):
    @abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def is_collection_existed(self, collection_name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_all_collections(self) -> Optional[List[str]]:
        raise NotImplementedError

    @abstractmethod
    async def get_collect_info(self, collection_name: str) -> Optional[Dict]:
        raise NotImplementedError

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def create_collection(
        self, collection_name: str, embedding_size: int, do_reset: bool
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        record_id: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def insert_many(
        self,
        collection_name: str,
        texts: List[str],
        vectors: List[List[float]],
        metadata: Optional[List[Dict[str, Any]]] = None,
        record_ids: Optional[List[str]] = None,
        batch_size: int = 50,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def search_by_vector(
        self, collection_name: str, vector: List[float], limit: int
    ) -> Optional[List[RetrivedfDocument]]:
        raise NotImplementedError
