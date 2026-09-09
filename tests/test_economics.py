from planner.economics import cost_for_activation, fx_convert
from planner.models import Activation


def activation(cost=100.0):
    return Activation("a", "A", "Done", "i", "p", cost, "EUR", 10000, 500, 100)


def test_activation_cost_is_fully_utilised_and_deterministic():
    assert cost_for_activation(activation()) == 100
    assert cost_for_activation(activation(0)) == 0


def test_fx_requires_explicit_non_target_rate():
    assert fx_convert(100, "EUR", "GBP", {"EUR": 0.86}) == 86

    try:
        fx_convert(100, "USD", "GBP", {})
    except ValueError as exc:
        assert "Missing FX rate" in str(exc)
    else:
        raise AssertionError("missing FX rate was silently accepted")
