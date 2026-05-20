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

STRUCTURAL COMPRESSION (for already-dense prompts):
- Drop articles: "a", "an", "the" when meaning is clear without them
- Merge list prefixes: "Include: X. Provide: Y." → "Cover X. Output Y."
- Use symbols: "greater than" → ">", "less than" → "<", "equal to" → "=="
- Condense phrasing: "estimated monthly AWS cost under 10k USD" → "AWS cost <$10k/mo"
- Use slashes for alternatives: "monthly and yearly" → "monthly/yearly"
- Merge adjacent lists into one when they share context
- Remove redundant verbs: "make sure to include" → "include"

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
Output: Write cover letter for Google SWE role.

Input: "Can you please write me a Python function that takes a list of dictionaries and returns only the ones where the value of the 'status' key is equal to 'active', and make sure to include type hints"
Output: Python function with type hints: filter list of dicts where status == 'active'.

Input: "Design a multi-tenant SaaS project management platform for 100k concurrent users using Node.js, PostgreSQL, Redis, Kafka, and Kubernetes. Include: authentication flow (JWT + OAuth), RBAC permissions, rate limiting, caching strategy, DB sharding, CI/CD pipeline, observability stack, disaster recovery, API versioning, cost optimization. Return: 1. high-level architecture 2. sequence diagram descriptions 3. markdown tables for services 4. estimated monthly AWS cost under 10k USD 5. security risks + mitigations."
Output: Design multi-tenant SaaS PM platform (100k concurrent, Node/PostgreSQL/Redis/Kafka/K8s). Cover: JWT+OAuth auth, RBAC, rate limiting, caching, DB sharding, CI/CD, observability, DR, API versioning, cost optimization. Output: architecture, sequence diagrams, service tables (markdown), AWS cost <$10k/mo, security risks+mitigations.

Input: "Create a step-by-step migration plan from a monolithic PHP application to microservices using Docker and Kubernetes with near-zero downtime. Include: strangler pattern, database migration strategy, rollback plans, observability, blue-green deployment, traffic splitting, secret management, cost analysis, timeline with weekly milestones. Return everything in markdown tables."
Output: Migration plan: monolith PHP→microservices (Docker/K8s), near-zero downtime. Cover: strangler pattern, DB migration, rollback, observability, blue-green deploy, traffic splitting, secrets, cost, weekly timeline. Format: markdown tables.

Input: "Build an end-to-end machine learning pipeline for fraud detection using Python and scikit-learn: preprocessing, feature engineering, handling class imbalance, cross-validation, hyperparameter tuning, explainability, drift detection, monitoring, deployment, retraining strategy. Use realistic assumptions and provide production considerations."
Output: End-to-end Python/scikit-learn fraud detection pipeline: preprocessing, feature engineering, class imbalance, cross-validation, hyperparameter tuning, explainability, drift detection, monitoring, deployment, retraining. Realistic assumptions, production considerations.

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
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
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
        """Strip filler, apply abbreviations, and compact structure.
        This saves input tokens and gives Gemini a cleaner signal."""
        import re

        s = text.strip()

        # ---- Layer 1: Filler phrase removal ----
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

        filler_words = [
            r"\breally\b", r"\bvery\b", r"\bjust\b", r"\bkindly\b",
            r"\bbasically\b", r"\bactually\b", r"\bhonestly\b",
            r"\bliterally\b",
        ]
        for word in filler_words:
            s = re.sub(word, "", s, flags=re.IGNORECASE)

        # ---- Layer 2: Phrase compaction (verified token-saving) ----
        compactions = [
            (r"\bmake sure to\b", "ensure"),
            (r"\bin order to\b", "to"),
            (r"\bas well as\b", "and"),
            (r"\bin addition to\b", "plus"),
            (r"\ba comprehensive and detailed\b", "detailed"),
            (r"\band also\b", "and"),
            (r"\bbut also\b", "and"),
            # Comparison shortcuts (save tokens)
            (r"\bgreater than\b", ">"),
            (r"\bless than\b", "<"),
            (r"\bequal to\b", "=="),
            (r"\bnot equal to\b", "!="),
        ]
        for pattern, replacement in compactions:
            s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)

        # Clean up whitespace
        s = re.sub(r"\s{2,}", " ", s).strip()
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
