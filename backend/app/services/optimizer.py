from google import genai
from google.genai import types

from app.core.config import Settings


SYSTEM_PROMPT = """You are a semantic prompt compression engine.

Your job: rewrite the user's prompt using the minimum tokens possible while preserving 100% of their intent, constraints, and required output format.

TARGET: 40-70% token reduction whenever possible.

COMPRESSION RULES:
- Remove filler words: "please", "kindly", "could you", "I was wondering", "I think", "really", "very", "just", "I would appreciate if"
- Remove politeness, hedging, and conversational phrasing
- Remove redundancy and repeated context
- Convert passive voice to active voice
- Prefer imperative instructions ("Explain X" not "Can you explain X")
- Convert verbose descriptions into compact semantic phrases
  Example: "a Python script that reads CSV files and removes duplicate rows" → "Python script removing duplicate CSV rows"
- Remove emotional padding unless it is the actual intent
  Example: "I really really urgently need help" → "Urgent:"

PRESERVATION RULES (never break these):
- Preserve core intent exactly — do NOT change what the user is asking for
- Preserve ALL explicit constraints and requirements
- Preserve technical terms, framework names, library names exactly
- Preserve requested output formats (JSON, markdown, tables, code blocks)
- Preserve important tone when it affects the output (e.g. "explain simply", "be formal")
- Do NOT add new requirements the user did not state
- Do NOT summarize vaguely — keep actionable specificity
- Do NOT drop constraints to make the prompt shorter

PRIORITY ORDER when you must choose:
1. Intent preservation
2. Constraint preservation
3. Technical accuracy
4. Output format preservation
5. Token minimization

EXAMPLES:

Input: "Please could you kindly help me to understand what the main differences are between REST and GraphQL APIs?"
Output: Differences between REST and GraphQL APIs?

Input: "I was wondering if you might be able to help me write a really good cover letter for a software engineering job at Google because I really want to get this job"
Output: Write a cover letter for a Google software engineering role.

Input: "Write a TypeScript React component using Tailwind CSS that displays a responsive pricing table with monthly and yearly billing toggle"
Output: Create responsive TypeScript React Tailwind pricing table with monthly/yearly billing toggle.

Input: "Can you please write me a Python function that takes a list of dictionaries and returns only the ones where the value of the 'status' key is equal to 'active', and make sure to include type hints"
Output: Python function with type hints: filter list of dicts where status == 'active'.

Input: "I need you to explain quantum entanglement to me in really simple terms that a 10 year old could understand, with a real world analogy"
Output: Explain quantum entanglement simply for a 10-year-old with a real-world analogy.

Input: "Can you help me debug this code? It keeps throwing a TypeError on line 23 when I pass a string instead of an integer and I'm not sure why"
Output: Debug TypeError on line 23: string passed instead of integer. Why?

Now compress this prompt. Output ONLY the compressed version, nothing else:"""


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
        """Preprocess → Gemini compress → postprocess."""
        cleaned = self._preprocess(raw_prompt)

        try:
            response = await self._get_client().aio.models.generate_content(
                model=self._model_name,
                contents=f"{SYSTEM_PROMPT}\n\n{cleaned}",
                config=types.GenerateContentConfig(
                    max_output_tokens=512,
                    temperature=0.2,
                    stop_sequences=["Input:", "Note:", "Explanation:", "---"],
                ),
            )
        except Exception as exc:
            raise OptimizerError(f"Gemini API error: {exc}") from exc

        optimized = self._postprocess(response.text or "")
        if not optimized:
            raise OptimizerError("Model returned an empty optimization.")
        return optimized

    # ---------- Pre/post processing ----------

    @staticmethod
    def _preprocess(text: str) -> str:
        """Strip common filler before sending to the model.
        This saves input tokens and gives Gemini a cleaner signal."""
        import re

        s = text.strip()

        # Filler phrases (order matters — longer patterns first)
        filler = [
            r"\bI was wondering if you could\b",
            r"\bI would really appreciate it if you could\b",
            r"\bI would appreciate it if you could\b",
            r"\bcould you (please |kindly )?",
            r"\bcan you (please |kindly )?",
            r"\bwould you (please |kindly )?",
            r"\bplease (could you |can you )?",
            r"\bI think (that )?",
            r"\bI was wondering if\b",
            r"\bI was hoping you could\b",
            r"\bI need you to\b",
            r"\bI want you to\b",
            r"\bif you don'?t mind\b",
            r"\bif that'?s okay\b",
            r"\bif possible\b",
        ]
        for pattern in filler:
            s = re.sub(pattern, "", s, flags=re.IGNORECASE)

        # Filler words (only when surrounded by word boundaries)
        filler_words = [
            r"\breally\b", r"\bvery\b", r"\bjust\b", r"\bkindly\b",
            r"\bbasically\b", r"\bactually\b", r"\bhonestly\b",
            r"\bliterally\b",
        ]
        for word in filler_words:
            s = re.sub(word, "", s, flags=re.IGNORECASE)

        # Clean up leftover whitespace
        s = re.sub(r"\s{2,}", " ", s).strip()
        # Fix leading lowercase after filler removal
        if s and s[0].islower():
            s = s[0].upper() + s[1:]

        return s

    @staticmethod
    def _postprocess(text: str) -> str:
        """Clean up model output — remove quotes, markdown, explanations."""
        s = text.strip()

        # Strip wrapping quotes
        if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'", "`"):
            s = s[1:-1].strip()

        # Remove markdown code fences
        if s.startswith("```"):
            s = s.split("\n", 1)[-1] if "\n" in s else s[3:]
        if s.endswith("```"):
            s = s[:-3]

        # Join valid lines, stop at rambling markers
        import re
        ramble_pattern = re.compile(
            r"^(Note:|Explanation:|Here|This |I |The original|Output:|---|\d+\.)",
            re.IGNORECASE,
        )
        kept = []
        for line in s.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if ramble_pattern.match(stripped) and kept:
                break  # model started explaining — stop
            kept.append(stripped)

        s = " ".join(kept) if kept else s

        return s.strip()
