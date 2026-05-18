from anthropic import APIError, AsyncAnthropic

from app.core.config import Settings


SYSTEM_PROMPT = """You are Tokn, a prompt compression and clarity engine.

Given a user's raw prompt, rewrite it so it is:
- Shorter: remove filler words, redundancy, and unnecessary politeness
- Clearer: specific intent, constraints, and desired output format when implied
- Precise: use direct, active language; keep all requirements and context

Rules:
- Preserve the user's goal, tone preference (if any), and all factual constraints
- Do NOT add new requirements the user did not imply
- Do NOT wrap the result in quotes, markdown fences, or explanations
- Return ONLY the optimized prompt text, nothing else"""


class OptimizerError(Exception):
    """Raised when optimization cannot be completed."""


class PromptOptimizerService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncAnthropic | None = None
        self._model = settings.anthropic_model
        self._max_tokens = settings.anthropic_max_tokens

    def _get_client(self) -> AsyncAnthropic:
        if not self._settings.anthropic_api_key:
            raise OptimizerError(
                "ANTHROPIC_API_KEY is not configured. Set it in your .env file."
            )
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        return self._client

    @property
    def model_name(self) -> str:
        return self._model

    async def optimize(self, raw_prompt: str) -> str:
        """Call Claude to compress and rephrase the prompt."""
        try:
            message = await self._get_client().messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": raw_prompt.strip(),
                    }
                ],
            )
        except APIError as exc:
            raise OptimizerError(f"Anthropic API error: {exc}") from exc

        text_blocks = [
            block.text
            for block in message.content
            if hasattr(block, "text") and block.text
        ]
        optimized = "".join(text_blocks).strip()
        if not optimized:
            raise OptimizerError("Model returned an empty optimization.")
        return optimized
