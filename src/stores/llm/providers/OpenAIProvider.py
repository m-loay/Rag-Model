from ..LLMEnums import OpenAIEnums
from ..LLMInterface import LLMInterface
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from typing import Any, List, Optional, cast, Dict
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

    def generate_text(
        self,
        prompt: str,
        chat_history: str,
        max_output_tokens: int,
        temperture: Optional[float] = None,
    ) -> Optional[str]:
        # 1) validation step
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set")
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
        user_msg = self.construct_prompt(prompt=prompt, role=OpenAIEnums.USER.value)
        correct_chat_history: List[Any] = [
            self.construct_prompt(prompt=chat_history, role=OpenAIEnums.SYSTEM.value)
        ]
        correct_chat_history.append(user_msg)

        # 4) send prompt to model
        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=cast(List[ChatCompletionMessageParam], correct_chat_history),
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
            return None
        message = response.choices[0].message
        content = message.content
        if not isinstance(content, str):
            self.logger.error(f"OpenAI response message content is {type(content)} not string")
            return None

        return content

    def embed_text(self, text: str, document_type: str) -> Optional[List[float]]:
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
        response = self.client.embeddings.create(input=text, model=self.embedding_model_id)

        # 3) validate response before return
        if (
            not response
            or not response.data
            or len(response.data) == 0
            or not response.data[0].embedding
        ):
            self.logger.error("Error while embedding text with OpenAI")
            return None
        return response.data[0].embedding

    def construct_prompt(self, prompt: str, role: str) -> Dict[str, str]:
        return {"role": role, "content": self.limit_txt(prompt)}
