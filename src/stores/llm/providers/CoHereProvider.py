from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypeEnums
from typing import Any, List, Optional, Dict
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
        chat_history: str,
        max_output_tokens: int,
        temperture: Optional[float] = None,
    ) -> Optional[str]:
        # 1) validation step
        if not self.client:
            self.logger.error("Cohere client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Cohere was not set")
            return None
        self.logger.info(f"generation model used is {self.generation_model_id}")

        # 2) set model parameters
        max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self.default_generation_max_output
        )

        temperture = temperture if temperture is not None else self.default_generation_temperture

        # 3) construct prompt
        correct_chat_history: List[Any] = [
            self.construct_prompt(prompt=chat_history, role=CoHereEnums.SYSTEM.value)
        ]

        # 4) send prompt to model
        response = self.client.chat(
            model=self.generation_model_id,
            chat_history=correct_chat_history,
            message=self.limit_txt(prompt),
            temperature=temperture,
            max_tokens=max_output_tokens,
        )

        # 5) Validate the response before return
        if not response or not response.text or len(response.text) == 0:
            self.logger.error("Error while embedding text with Cohere")
            return None
        return response.text

    def embed_text(self, text: str, document_type: str) -> Optional[List[float]]:
        # 1) validate step
        if not self.client:
            self.logger.error("Cohere client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for Cohere was not set")
            return None
        self.logger.info(
            f"embedding model used is {self.embedding_model_id} with size {self.embedding_model_size}"
        )

        input_type = CoHereEnums.DOCUMENT.value
        if document_type == DocumentTypeEnums.QUERY.value:
            input_type = CoHereEnums.QUERY.value

        # 2) send text to embeddings
        response = self.client.embed(
            model=self.embedding_model_id,
            texts=[self.limit_txt(text)],
            input_type=input_type,
            embedding_types=["float"],
        )

        # 3) validate response before return
        if response is None or response.embeddings is None:
            self.logger.error("Cohere returned empty response")
            return None

        embeddingss = response.embeddings.float  # type: ignore
        embeddings_list: List[float] = embeddingss[0]
        if not embeddings_list or len(embeddings_list) == 0:
            self.logger.error("Cohere returned empty embeddings")
            return None

        return embeddings_list

    def construct_prompt(self, prompt: str, role: str) -> Dict[str, str]:
        return {"role": role, "text": self.limit_txt(prompt)}
