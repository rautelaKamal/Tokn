from functools import lru_cache

from app.core.config import get_settings
from app.services.cost import CostCalculator
from app.services.optimizer import PromptOptimizerService
from app.services.tokenizer import TokenCounter


@lru_cache
def get_token_counter() -> TokenCounter:
    settings = get_settings()
    return TokenCounter(encoding_name=settings.tiktoken_encoding)


@lru_cache
def get_cost_calculator() -> CostCalculator:
    settings = get_settings()
    return CostCalculator(
        input_cost_per_million=settings.input_cost_per_million,
        output_cost_per_million=settings.output_cost_per_million,
    )


@lru_cache
def get_optimizer_service() -> PromptOptimizerService:
    """Cached singleton — avoids creating a new Gemini client per request."""
    return PromptOptimizerService(get_settings())
