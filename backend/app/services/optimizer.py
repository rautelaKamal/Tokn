from google import genai
from google.genai import types

from app.core.config import Settings


SYSTEM_PROMPT = """You are a semantic prompt compression engine.

Your job: rewrite the user's prompt using the minimum tokens possible while preserving 100% of their intent, constraints, and required output format.

TARGET: 40-70% token reduction whenever possible.

COMPRESSION RULES:
- Remove filler: "please", "kindly", "could you", "I was wondering", "I think", "really", "very", "just"
- Remove politeness, hedging, conversational phrasing
- Remove redundancy and repeated context
- Prefer imperative: "Explain X" not "Can you explain X"
- Remove implicit subjects: "I want you to write" → "Write", "Can you give me" → ""
- Remove articles (the, a, an) unless grammatically critical
- Use colons for topic intro: "Python:" not "about Python,"
- Use slashes for comparisons: "X vs Y" not "differences between X and Y"
- Replace verbose self-descriptions with compact equivalents:
  "I don't understand" + "from 0" both mean beginner → "for a complete beginner"
- Merge redundant skill signals into one: keep only the clearest expression
- Stack constraints with commas after colon: "[type]: [c1], [c2], [c3]"
- Replace "write me a/give me a/create a" with output type + colon
- Convert verb phrases to noun phrases when shorter:
  "write code that sorts" → "list sorting code"
  "explain how X works" → "how X works"

STRUCTURAL COMPRESSION (dense prompts):
- Merge list prefixes: "Include: X. Provide: Y." → "Cover X. Output Y."
- Use symbols: "greater than" → ">", "less than" → "<", "equal to" → "=="
- Condense phrasing: "estimated monthly AWS cost under 10k USD" → "AWS cost <$10k/mo"
- Merge adjacent lists sharing context
- Remove redundant verbs: "make sure to include" → "include"

PRESERVATION RULES (never break these):
- Preserve core intent exactly
- Preserve ALL explicit constraints and requirements
- Preserve technical terms, framework names, library names exactly
- Preserve requested output formats (JSON, markdown, tables, code blocks)
- Preserve skill level intent — "I'm a beginner", "explain simply", "from scratch" signal user level. Keep the meaning (use compact form), never drop it entirely.
- Do NOT add new requirements the user did not state
- Do NOT summarize vaguely — keep actionable specificity
- Do NOT drop constraints to make the prompt shorter

PRIORITY ORDER:
1. Intent preservation
2. Constraint preservation
3. Technical accuracy
4. Output format preservation
5. Token minimization

EXAMPLES:

Input: "Please could you kindly help me to understand what the main differences are between REST and GraphQL APIs?"
Output: REST vs GraphQL: differences?

Input: "I was wondering if you might be able to help me write a really good cover letter for a software engineering job at Google because I really want to get this job"
Output: Cover letter for Google SWE role.

Input: "Can you please write me a Python function that takes a list of dictionaries and returns only the ones where the value of the 'status' key is equal to 'active', and make sure to include type hints"
Output: Python function with type hints: filter dicts where status == 'active'.

Input: "i dont understand the topic, explain in depth and detail, from 0"
Output: Explain topic in depth for a complete beginner.

Input: "I'm a complete beginner and I really need you to please explain how Docker containers work in simple terms"
Output: Docker containers: explain simply for a beginner.

Input: "Can you give me a list of the best Python libraries for data science with a brief description of each one"
Output: List best Python data science libraries with descriptions.

Input: "I need you to write code that takes a JSON file and converts it into a CSV file"
Output: JSON to CSV converter code.

Input: "Can you help me understand why my React component keeps re-rendering even when the props haven't changed"
Output: Why does React component re-render with unchanged props?

Input: "Write a REST API in Python using FastAPI that handles user authentication and returns JSON responses"
Output: FastAPI REST API: user auth, JSON responses.

Input: "Design a multi-tenant SaaS project management platform for 100k concurrent users using Node.js, PostgreSQL, Redis, Kafka, and Kubernetes. Include: authentication flow (JWT + OAuth), RBAC permissions, rate limiting, caching strategy, DB sharding, CI/CD pipeline, observability stack, disaster recovery, API versioning, cost optimization. Return: 1. high-level architecture 2. sequence diagram descriptions 3. markdown tables for services 4. estimated monthly AWS cost under 10k USD 5. security risks + mitigations."
Output: Design multi-tenant SaaS PM platform (100k concurrent, Node/PostgreSQL/Redis/Kafka/K8s). Cover: JWT+OAuth auth, RBAC, rate limiting, caching, DB sharding, CI/CD, observability, DR, API versioning, cost optimization. Output: architecture, sequence diagrams, service tables (markdown), AWS cost <$10k/mo, security risks+mitigations.

Input: "Create a step-by-step migration plan from a monolithic PHP application to microservices using Docker and Kubernetes with near-zero downtime. Include: strangler pattern, database migration strategy, rollback plans, observability, blue-green deployment, traffic splitting, secret management, cost analysis, timeline with weekly milestones. Return everything in markdown tables."
Output: Migration plan: monolith PHP→microservices (Docker/K8s), near-zero downtime. Cover: strangler pattern, DB migration, rollback, observability, blue-green deploy, traffic splitting, secrets, cost, weekly timeline. Format: markdown tables.

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
