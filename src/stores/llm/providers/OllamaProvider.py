from typing import Optional
from .OpenAIProvider import OpenAIProvider


class OllamaProvider(OpenAIProvider):
    def __init__(
        self,
        api_key: str,
        api_url: str | None,
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
