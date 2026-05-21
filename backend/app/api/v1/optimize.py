import hashlib
import time
from collections import OrderedDict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import (
    get_cost_calculator,
    get_optimizer_service,
    get_token_counter,
)
from app.core.config import get_settings
from app.schemas.optimize import OptimizeRequest, OptimizeResponse, TokenStats
from app.services.cost import CostCalculator
from app.services.optimizer import OptimizerError, PromptOptimizerService
from app.services.tokenizer import TokenCounter

router = APIRouter()

# --- In-memory LRU cache for optimized prompts ---
_prompt_cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
_settings = None


def _get_cache_settings():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def _get_cached(prompt: str) -> str | None:
    """Return cached optimization result if still valid."""
    settings = _get_cache_settings()
    key = _cache_key(prompt)
    if key not in _prompt_cache:
        return None
    result, timestamp = _prompt_cache[key]
    if time.time() - timestamp > settings.prompt_cache_ttl_seconds:
        _prompt_cache.pop(key, None)
        return None
    # Move to end (most recently used)
    _prompt_cache.move_to_end(key)
    return result


def _set_cached(prompt: str, optimized: str) -> None:
    """Store optimization result in cache."""
    settings = _get_cache_settings()
    key = _cache_key(prompt)
    _prompt_cache[key] = (optimized, time.time())
    _prompt_cache.move_to_end(key)
    # Evict oldest entries if over capacity
    while len(_prompt_cache) > settings.prompt_cache_maxsize:
        _prompt_cache.popitem(last=False)


limiter = Limiter(key_func=get_remote_address)


@router.post("/", response_model=OptimizeResponse)
@limiter.limit("10/minute")
async def optimize_prompt(
    request: Request,
    payload: OptimizeRequest,
    token_counter: TokenCounter = Depends(get_token_counter),
    cost_calculator: CostCalculator = Depends(get_cost_calculator),
    optimizer: PromptOptimizerService = Depends(get_optimizer_service),
) -> OptimizeResponse:
    """
    Compress and rephrase a prompt via Claude, then return token and cost deltas.
    Results are cached for 1 hour to avoid redundant API calls.
    """
    original = payload.prompt.strip()
    tokens_before = token_counter.count(original)

    # Check cache first — avoid paying for the same prompt twice
    cached = _get_cached(original)
    if cached is not None:
        optimized = cached
    else:
        try:
            optimized = await optimizer.optimize(original, level=payload.level or "balanced")
        except OptimizerError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
        _set_cached(original, optimized)

    tokens_after = token_counter.count(optimized)
    tokens_saved = max(0, tokens_before - tokens_after)

    cost_before = cost_calculator.estimate_prompt_cost(tokens_before)
    cost_after = cost_calculator.estimate_prompt_cost(tokens_after)
    cost_saved = round(max(0.0, cost_before - cost_after), 6)

    compression_ratio = (
        round(tokens_saved / tokens_before, 4) if tokens_before > 0 else 0.0
    )

    model_label = payload.model or optimizer.model_name

    return OptimizeResponse(
        original_prompt=original,
        optimized_prompt=optimized,
        tokens_before=TokenStats(
            tokens=tokens_before,
            estimated_cost_usd=cost_before,
        ),
        tokens_after=TokenStats(
            tokens=tokens_after,
            estimated_cost_usd=cost_after,
        ),
        tokens_saved=tokens_saved,
        cost_saved_usd=cost_saved,
        compression_ratio=compression_ratio,
        model_used=model_label,
        encoding_used=token_counter.encoding_name,
    )
