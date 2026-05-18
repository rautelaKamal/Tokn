from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=32_000,
        description="Raw prompt text to optimize",
    )
    model: str | None = Field(
        default=None,
        description="Optional override for cost estimation model label",
    )


class TokenStats(BaseModel):
    tokens: int
    estimated_cost_usd: float


class OptimizeResponse(BaseModel):
    original_prompt: str
    optimized_prompt: str
    tokens_before: TokenStats
    tokens_after: TokenStats
    tokens_saved: int
    cost_saved_usd: float
    compression_ratio: float = Field(
        description="Fraction of tokens removed (0–1); 0.2 = 20% smaller"
    )
    model_used: str
    encoding_used: str
