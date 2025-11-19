from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict


class LLMInterface(ABC):
    @abstractmethod
    def set_generation_model(self, model_id: Optional[str]) -> None:
        pass

    @abstractmethod
    def set_embeddings_model(self, model_id: Optional[str], embedding_size: Optional[int]) -> None:
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        chat_history: List[Any],
        max_output_tokens: int,
        temperture: Optional[float] = None,
    ) -> Optional[str]:
        pass

    @abstractmethod
    def embed_text(self, text: str, document_type: str) -> Any:
        pass

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str) -> Dict[str, str]:
        pass
