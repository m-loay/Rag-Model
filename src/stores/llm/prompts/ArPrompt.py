from string import Template
from .BasePrompt import BasePrompt


class ArPrompt(BasePrompt):
    _system_tpl = Template(
        "\n".join(
            [
                "أنت مساعد لتوليد رد للمستخدم.",
                "ستحصل على مجموعة من المستندات المرتبطة باستفسار المستخدم.",
                "عليك توليد رد بناءً على المستندات المقدَّمة.",
                "تجاهل المستندات التي لا تتعلق باستفسار المستخدم.",
                "يمكنك الاعتذار للمستخدم إذا لم تتمكن من توليد رد.",
                "عليك توليد الرد بنفس لغة استفسار المستخدم.",
                "كن مؤدبًا ومحترمًا في التعامل مع المستخدم.",
                "كن دقيقًا ومختصرًا في ردك. تجنَّب المعلومات غير الضرورية.",
            ]
        )
    )

    _document_tpl = Template(
        "\n".join(
            [
                "## المستند رقم: $doc_num",
                "### المحتوى: $chunk_text",
            ]
        )
    )

    _footer_tpl = Template(
        "\n".join(
            [
                "قدِّم إجابة مفيدة ومختصرة للمستخدم.",
                "إذا لم تكن المستندات كافية للإجابة بدقة، فاذكر ذلك بوضوح.",
                "## الإجابة:",
            ]
        )
    )

    def system_prompt(self) -> str:
        return self._system_tpl.substitute({})

    def document_prompt(self, doc_num: int, chunk_text: str) -> str:
        return self._document_tpl.substitute({"doc_num": doc_num, "chunk_text": chunk_text})

    def footer_prompt(self, query: str) -> str:
        return self._footer_tpl.substitute({})
