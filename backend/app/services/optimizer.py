from google import genai
from google.genai import types

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
        self._model_name = settings.gemini_model
        self._client = None

    def _get_client(self) -> genai.Client:
        if not self._settings.gemini_api_key:
            raise OptimizerError(
                "GEMINI_API_KEY is not configured. Set it in your .env file. "
                "Get a free key at https://aistudio.google.com"
            )
        if self._client is None:
            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    @property
    def model_name(self) -> str:
        return self._model_name

    async def optimize(self, raw_prompt: str) -> str:
        """Call Gemini to compress and rephrase the prompt."""
        try:
            response = await self._get_client().aio.models.generate_content(
                model=self._model_name,
                contents=raw_prompt.strip(),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=1024,
                    temperature=0.3,
                ),
            )
        except Exception as exc:
            raise OptimizerError(f"Gemini API error: {exc}") from exc

        optimized = (response.text or "").strip()
        if not optimized:
            raise OptimizerError("Model returned an empty optimization.")
        return optimized
