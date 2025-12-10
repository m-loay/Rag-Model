import cohere
from cohere.types import Message
import logging
from ..LLMInterface import LLMInterface, ChatMessage
from ..LLMEnums import CoHereEnums, DocumentTypeEnums
from typing import Union, List, Optional, cast, Tuple


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
        system_prompt: str,
        max_output_tokens: int,
        temperture: Optional[float] = None,
    ) -> Tuple[Optional[str], List[ChatMessage]]:
        chat_history: List[ChatMessage] = []
        # 1) validation step
        if not self.client:
            self.logger.error("Cohere client was not set")
            return None, chat_history

        if not self.generation_model_id:
            self.logger.error("Generation model for Cohere was not set")
            return None, chat_history
        self.logger.info(f"generation model used is {self.generation_model_id}")

        # 2) set model parameters
        max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self.default_generation_max_output
        )

        temperture = temperture if temperture is not None else self.default_generation_temperture

        # 3) construct prompt
        system_msg = self.construct_prompt(prompt=system_prompt, role=CoHereEnums.SYSTEM.value)
        user_msg = self.construct_prompt(prompt=prompt, role=CoHereEnums.USER.value)
        chat_history.append(system_msg)
        chat_history.append(user_msg)

        cohere_history: List[Message] = [
            cast(
                Message,
                {
                    "role": msg["role"],
                    "message": msg["text"],
                },
            )
            for msg in chat_history
        ]

        # 4) send prompt to model
        response = self.client.chat(
            model=self.generation_model_id,
            chat_history=cohere_history,
            message=prompt,
            temperature=temperture,
            max_tokens=max_output_tokens,
        )

        # 5) Validate the response before return
        if not response or not response.text or len(response.text) == 0:
            self.logger.error("Error while embedding text with Cohere")
            return None, chat_history
        return response.text, chat_history

    def embed_text(
        self, text: Union[str, List[str]], document_type: str
    ) -> Optional[List[List[float]]]:
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
        if isinstance(text, str):
            texts: List[str] = [text]
        else:
            texts = text
        response = self.client.embed(
            model=self.embedding_model_id,
            texts=texts,
            input_type=input_type,
            embedding_types=["float"],
        )

        # 3) validate response before return
        if response is None or response.embeddings is None:
            self.logger.error("Cohere returned empty response")
            return None

        embeddings_2d: List[List[float]] = response.embeddings.float  # type: ignore
        if not embeddings_2d or not embeddings_2d[0]:
            self.logger.error("Cohere returned empty embeddings")
            return None

        return embeddings_2d

    def construct_prompt(self, prompt: str, role: str) -> ChatMessage:
        return {"role": role, "text": prompt}
