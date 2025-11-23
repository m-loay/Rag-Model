from string import Template
from .BasePrompt import BasePrompt


class EnPrompt(BasePrompt):
    _system_tpl = Template(
        "\n".join(
            [
                "You are an assistant to generate a response for the user.",
                "You will be provided with a set of documents associated with the user's query.",
                "You have to generate a response based on the documents provided.",
                "Ignore the documents that are not relevant to the user's query.",
                "You can apologize to the user if you are not able to generate a response.",
                "You have to generate the response in the same language as the user's query.",
                "Be polite and respectful to the user.",
                "Be precise and concise in your response. Avoid unnecessary information.",
            ]
        )
    )

    _document_tpl = Template(
        "\n".join(
            [
                "## Document No: $doc_num",
                "### Content: $chunk_text",
            ]
        )
    )

    _footer_tpl = Template(
        "\n".join(
            [
                "Provide a helpful and concise answer for the user.",
                "If the documents are not sufficient, clearly say so.",
                "## Answer:",
            ]
        )
    )

    def system_prompt(self) -> str:
        return self._system_tpl.substitute({})

    def document_prompt(self, doc_num: int, chunk_text: str) -> str:
        return self._document_tpl.substitute({"doc_num": doc_num, "chunk_text": chunk_text})

    # keep signature with query for compatibility, even if we don't use it
    def footer_prompt(self, query: str) -> str:
        return self._footer_tpl.substitute({})
