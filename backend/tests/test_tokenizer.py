from app.services.cost import CostCalculator
from app.services.tokenizer import TokenCounter


def test_token_counter_empty() -> None:
    counter = TokenCounter()
    assert counter.count("") == 0


def test_token_counter_reduces_on_shorter_text() -> None:
    counter = TokenCounter()
    long_text = "Please could you kindly help me with " * 5
    short_text = "Help me with task X."
    assert counter.count(short_text) < counter.count(long_text)


def test_cost_savings() -> None:
    calc = CostCalculator(3.0, 15.0)
    assert calc.savings(1000, 600) == calc.estimate_input_cost(400)
