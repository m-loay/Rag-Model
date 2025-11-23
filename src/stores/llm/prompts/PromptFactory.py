from typing import Optional
from .BasePrompt import BasePrompt
from .EnPrompt import EnPrompt
from .ArPrompt import ArPrompt


class RagPromptFactory:
    @staticmethod
    def get_rag_prompt(language: Optional[str] = None) -> BasePrompt:
        if not language:
            return EnPrompt()

        lang = language.lower()

        if lang.startswith("ar"):
            return ArPrompt()

        return EnPrompt()
