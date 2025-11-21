from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict


class LLMInterface(ABC):
    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        default_input_max_chars: int = 1000,
        default_generation_max_output: int = 1000,
        default_generation_temperture: float = 0.1,
    ) -> None:
        # Common config
        self.api_key: str = api_key
        self.api_url: Optional[str] = api_url

        # Model config
        self.generation_model_id: str
        self.embedding_model_id: str
        self.embedding_model_size: int

        # Defaults
        self.default_input_max_chars: int = default_input_max_chars
        self.default_generation_max_output: int = default_generation_max_output
        self.default_generation_temperture: float = default_generation_temperture

    # -------- Common interface methods -----------------------

    def set_generation_model(self, model_id: str) -> None:
        self.generation_model_id = model_id

    def set_embeddings_model(self, model_id: str, embedding_size: int) -> None:
        self.embedding_model_id = model_id
        self.embedding_model_size = embedding_size

    def limit_txt(self, text: str) -> str:
        return text[: self.default_input_max_chars].strip()

    def construct_prompt(self, prompt: str, role: str) -> Dict[str, str]:
        return {"role": role, "content": self.limit_txt(prompt)}

    # -------- Provider-specific behaviour --------------------

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
    def embed_text(self, text: str, document_type: str) -> Optional[List[float]]:
        pass
