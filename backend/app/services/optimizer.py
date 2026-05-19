from google import genai
from google.genai import types

from app.core.config import Settings


SYSTEM_PROMPT = """You are an expert prompt compressor. Your job is to rewrite prompts to be as short as possible while preserving 100% of the intent and meaning.

Rules:
- Remove filler words: "please", "kindly", "could you", "I was wondering", "I think", "really", "very", "just"
- Remove redundant phrases: "as mentioned", "as I said", "in other words"
- Convert passive to active voice
- Remove excessive politeness and hedging
- Keep technical terms exact — never paraphrase those
- Do NOT add new requirements the user did not imply
- Output ONLY the compressed prompt, nothing else. No explanation, no quotes, no markdown fences.

Examples:
Input: "Please could you kindly help me to understand what the main differences are between REST and GraphQL APIs?"
Output: Differences between REST and GraphQL APIs?

Input: "I was wondering if you might be able to help me write a really good cover letter for a software engineering job at Google because I really want to get this job"
Output: Write a cover letter for a Google software engineering role.

Input: "Can you please explain to me how machine learning works in simple terms that a beginner could understand?"
Output: Explain machine learning simply for beginners.

Input: "I would really appreciate it if you could help me debug this Python code that keeps throwing an IndexError when I try to iterate over a list of items"
Output: Debug Python IndexError when iterating over a list.

Input: "Could you please write me a comprehensive and detailed summary of the key points from this research paper about transformer architectures in natural language processing?"
Output: Summarize key points of this transformer architecture NLP paper.

Now compress this prompt:"""


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
                contents=f"{SYSTEM_PROMPT}\n\n{raw_prompt.strip()}",
                config=types.GenerateContentConfig(
                    max_output_tokens=1024,
                    temperature=0.2,
                ),
            )
        except Exception as exc:
            raise OptimizerError(f"Gemini API error: {exc}") from exc

        optimized = (response.text or "").strip()
        if not optimized:
            raise OptimizerError("Model returned an empty optimization.")
        return optimized
