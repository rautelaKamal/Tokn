class CostCalculator:
    """Estimates USD cost from token counts using configurable per-million rates."""

    def __init__(
        self,
        input_cost_per_million: float,
        output_cost_per_million: float,
    ) -> None:
        self._input_rate = input_cost_per_million / 1_000_000
        self._output_rate = output_cost_per_million / 1_000_000

    def estimate_input_cost(self, tokens: int) -> float:
        return round(tokens * self._input_rate, 6)

    def estimate_output_cost(self, tokens: int) -> float:
        return round(tokens * self._output_rate, 6)

    def estimate_prompt_cost(self, tokens: int, *, as_input: bool = True) -> float:
        """Prompt text is billed as input tokens when sent to an LLM."""
        if as_input:
            return self.estimate_input_cost(tokens)
        return self.estimate_output_cost(tokens)

    def savings(self, tokens_before: int, tokens_after: int) -> float:
        saved = max(0, tokens_before - tokens_after)
        return self.estimate_input_cost(saved)
