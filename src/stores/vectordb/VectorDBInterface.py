from abc import ABC, abstractmethod
from typing import Optional, Any, List, Dict

from huggingface_hub import delete_collection


class VectorDBInterface(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_collection_existed(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def list_all_collections(self) -> Optional[List[str]]:
        pass

    @abstractmethod
    def get_collect_info(self, collection_name: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool) -> bool:
        pass

    @abstractmethod
    def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: List,
        metadta: Optional[Dict] = None,
        record_id: Optional[str] = None,
    ) -> bool:
        pass

    @abstractmethod
    def insert_many(
        self,
        collection_name: str,
        texts: List[str],
        vectors: List[List[float]],
        metadta: Optional[List[Dict]] = None,
        record_ids: Optional[List[str]] = None,
        batch_size: int = 50,
    ) -> bool:
        pass

    def search_by_vector(
        self, collection_name: str, vector: List, limit: int
    ) -> Optional[List[Any]]:
        pass
