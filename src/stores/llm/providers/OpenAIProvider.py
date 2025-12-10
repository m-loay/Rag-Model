from ..LLMEnums import OpenAIEnums
from ..LLMInterface import LLMInterface, ChatMessage
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from typing import Any, List, Optional, Tuple, cast, Union
import logging


class OpenAIProvider(LLMInterface):
    def __init__(
        self,
        api_key: str,
        api_url: Optional[str],
        default_input_max_chars: int = 1000,
        default_generation_max_output: int = 1000,
        default_generation_temperture: float = 0.1,
    ) -> None:
        super().__init__(
            api_key=api_key,
            api_url=api_url,
            default_input_max_chars=default_input_max_chars,
            default_generation_max_output=default_generation_max_output,
            default_generation_temperture=default_generation_temperture,
        )
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url)
        self.logger = logging.getLogger(__name__)
        self.enums = OpenAIEnums

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
            self.logger.error("OpenAI client was not set")
            return None, chat_history

        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set")
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
        system_msg = self.construct_prompt(prompt=system_prompt, role=OpenAIEnums.SYSTEM.value)
        user_msg = self.construct_prompt(prompt=prompt, role=OpenAIEnums.USER.value)
        chat_history.append(system_msg)
        chat_history.append(user_msg)

        # 4) send prompt to model
        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=cast(List[ChatCompletionMessageParam], chat_history),
            max_tokens=max_output_tokens,
            temperature=temperture,
        )

        # 5) Validate the response before return
        if (
            not response
            or not response.choices
            or len(response.choices) == 0
            or response.choices[0].message is None
        ):
            self.logger.error("Error while generating text with OpenAI")
            return None, chat_history
        message = response.choices[0].message
        content = message.content
        if not isinstance(content, str):
            self.logger.error(f"OpenAI response message content is {type(content)} not string")
            return None, chat_history

        # 6) add content as assistant message to chat history
        assistant_message = self.construct_prompt(prompt=content, role=OpenAIEnums.ASSISTANT.value)
        chat_history.append(assistant_message)

        return content, chat_history

    def embed_text(
        self, text: Union[str, List[str]], document_type: str
    ) -> Optional[List[List[float]]]:
        # 1) validate step
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for OpenAI was not set")
            return None

        self.logger.info(
            f"embedding model used is {self.embedding_model_id} with size {self.embedding_model_size}"
        )

        # 2) send text to embeddings
        if isinstance(text, str):
            text = [text]
        response = self.client.embeddings.create(input=text, model=self.embedding_model_id)

        # 3) validate response before return
        if (
            not response
            or not response.data
            or len(response.data) == 0
            or len(response.data) != len(text)
            or not response.data[0].embedding
        ):
            self.logger.error("Error while embedding text with OpenAI")
            return None

        # ensure all embeddings are present
        embeddings: List[List[float]] = []
        for i, rec in enumerate(response.data):
            if not rec.embedding:
                self.logger.error(f"Missing embedding at index {i}")
                return None
            embeddings.append(rec.embedding)
        return embeddings

    def construct_prompt(self, prompt: str, role: str) -> ChatMessage:
        return {"role": role, "content": prompt}
