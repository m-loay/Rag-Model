from abc import ABC, abstractmethod
from typing import Sequence


class BasePrompt(ABC):
    @abstractmethod
    def system_prompt(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def document_prompt(self, doc_num: int, chunk_text: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def footer_prompt(self, query: str) -> str:
        raise NotImplementedError

    def build_full_prompt(self, query: str, documents: Sequence[str]) -> str:
        if not documents:
            # Fallback – no docs retrieved
            return (
                f"User query: {query}\n\n"
                "No supporting documents were retrieved. "
                "Explain to the user that you cannot answer confidently."
            )

        documents_block = "\n".join(
            self.document_prompt(doc_num=i + 1, chunk_text=text) for i, text in enumerate(documents)
        )

        footer = self.footer_prompt(query=query)

        # This is the RAG behaviour we just verified works well
        return (
            f"User query: {query}\n\n"
            "Answer the user based ONLY on the following documents.\n\n"
            f"{documents_block}\n\n"
            f"{footer}"
        )
