from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypeEnums
from typing import Any, List, Optional
import cohere
import logging


class CoHereProvider(LLMInterface):
    def __init__(
        self,
        api_key: str,
        default_input_max_chars: int = 1000,
        default_generation_max_output: int = 1000,
        default_generation_temperture: float = 0.1,
    ) -> None:
        super().__init__(
            api_key=api_key,
            api_url=None,
            default_input_max_chars=default_input_max_chars,
            default_generation_max_output=default_generation_max_output,
            default_generation_temperture=default_generation_temperture,
        )
        self.client = cohere.Client(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

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

    def embed_text(self, text: str, document_type: str) -> Optional[List[float]]:
        if not self.client:
            self.logger.error("Cohere client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for Cohere was not set")
            return None

        input_type = CoHereEnums.DOCUMENT.value
        if document_type == DocumentTypeEnums.QUERY.value:
            input_type = CoHereEnums.QUERY.value

        response = self.client.embed(
            model=self.embedding_model_id,
            texts=[self.limit_txt(text)],
            input_type=input_type,
            embedding_types=["float"],
        )

        if response is None or response.embeddings is None:
            self.logger.error("Cohere returned empty response")
            return None

        embeddingss = response.embeddings.float  # type: ignore
        embeddings_list: List[float] = embeddingss[0]
        if not embeddings_list or len(embeddings_list) == 0:
            self.logger.error("Cohere returned empty embeddings")
            return None

        # We passed a single text, so take the first vector
        return embeddings_list
