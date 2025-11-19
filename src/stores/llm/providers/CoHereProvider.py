from LLMInterface import LLMInterface
from LLMEnums import CoHereEnums, DocumentTypeEnums
from typing import Any, List, Optional
import cohere
import logging


class CoHereProvider(LLMInterface):
    def __init__(
        self,
        api_key: Optional[str],
        default_input_max_chars: Optional[int] = 1000,
        default_generation_max_output: Optional[int] = 1000,
        default_generation_temperture: Optional[float] = 0.1,
    ) -> None:
        self.api_key = api_key
        self.generation_model_id: Optional[str] = None
        self.embedding_model_id: Optional[str] = None
        self.embedding_model_size: Optional[int] = 1000
        self.default_input_max_chars: Optional[int] = default_input_max_chars
        self.default_generation_max_output: Optional[int] = default_generation_max_output
        self.default_generation_temperture: Optional[float] = default_generation_temperture

        self.client = cohere.Client(api_key=self.api_key)

        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: Optional[str]) -> None:
        self.generation_model_id = model_id

    def set_embeddings_model(self, model_id: Optional[str], embedding_size: Optional[int]) -> None:
        self.embedding_model_id = model_id
        self.embedding_model_size = embedding_size

    def generate_text(
        self,
        prompt: str,
        chat_history: List[Any],
        max_output_tokens: int,
        temperture: Optional[float] = None,
    ) -> Optional[str]:
        if not self.client:
            self.logger.error("Cohere client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Cohere was not set")
            return None

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self.default_generation_max_output
        )

        temperture = temperture if temperture is not None else self.default_generation_temperture

        response = self.client.chat(
            model=self.generation_model_id,
            chat_history=chat_history,
            message=self.limit_txt(prompt),
            temperature=temperture,
            max_tokens=max_output_tokens,
        )
        if not response or not response.text or len(response.text) == 0:
            self.logger.error("Error while embedding text with OpenAI")
            return None
        return response.text

    def embed_text(self, text: str, document_type: str) -> Any:
        if not self.client:
            self.logger.error("Cohere client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for Cohere was not set")
            return None

        input_type = CoHereEnums.DOCUMENT.value
        if document_type == DocumentTypeEnums.QUERY:
            input_type = CoHereEnums.QUERY.value

        response = self.client.embed(
            model=self.embedding_model_id,
            texts=[self.limit_txt(text)],
            input_type=input_type,
            embedding_types=["float"],
        )

        if not response or not response.embeddings == 0:
            return None

        return response.embeddings

    def limit_txt(self, text: str) -> str:
        return text[: self.default_input_max_chars].strip()

    def construct_prompt(self, prompt: str, role: str) -> dict[str, str]:
        return {"role": role, "content": self.limit_txt(prompt)}
