from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_cost_calculator,
    get_optimizer_service,
    get_token_counter,
)
from app.schemas.optimize import OptimizeRequest, OptimizeResponse, TokenStats
from app.services.cost import CostCalculator
from app.services.optimizer import OptimizerError, PromptOptimizerService
from app.services.tokenizer import TokenCounter

router = APIRouter()


@router.post("/", response_model=OptimizeResponse)
async def optimize_prompt(
    payload: OptimizeRequest,
    token_counter: TokenCounter = Depends(get_token_counter),
    cost_calculator: CostCalculator = Depends(get_cost_calculator),
    optimizer: PromptOptimizerService = Depends(get_optimizer_service),
) -> OptimizeResponse:
    """
    Compress and rephrase a prompt via Claude, then return token and cost deltas.
    """
    original = payload.prompt.strip()
    tokens_before = token_counter.count(original)

    try:
        optimized = await optimizer.optimize(original)
    except OptimizerError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

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
