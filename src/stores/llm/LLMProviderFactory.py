from .LLMEnums import LLMEnums
from .LLMInterface import LLMInterface
from .providers import OpenAIProvider, CoHereProvider
from helpers.config import Settings


class LLMProviderFactory:
    def __init__(self, config: Settings) -> None:
        self.config: Settings = config

    def create(self, provider: str) -> LLMInterface:
        if provider == LLMEnums.OPENAI.value:
            return OpenAIProvider(
                api_key=self.config.OPENAI_API_KEY,
                api_url=self.config.OPENAI_API_URL,
                default_input_max_chars=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperture=self.config.GENERATION_DAFAULT_TEMPERATURE,
            )

        if provider == LLMEnums.COHERE.value:
            return CoHereProvider(
                api_key=self.config.COHERE_API_KEY,
                default_input_max_chars=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperture=self.config.GENERATION_DAFAULT_TEMPERATURE,
            )
        raise ValueError(f"Unknown LLM provider: {provider}")
