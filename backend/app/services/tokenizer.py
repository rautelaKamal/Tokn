import tiktoken


class TokenCounter:
    """Counts tokens using tiktoken (BPE estimate aligned with many LLM APIs)."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding_name = encoding_name
        self._encoding = tiktoken.get_encoding(encoding_name)

    @property
    def encoding_name(self) -> str:
        return self._encoding_name

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encoding.encode(text))
