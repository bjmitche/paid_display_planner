from planner.economics import cost_for_activation, fx_convert
from planner.models import Activation


def activation(cost=100.0):
    return Activation("a", "A", "Done", "i", "p", cost, "EUR", 10000, 500, 100)


def test_fixed_cost_is_deterministic():
    assert cost_for_activation(activation(), "Fixed", 20000, 100) == 100


def test_cpm_cost_uses_impressions():
    assert cost_for_activation(activation(4), "CPM", 25000, 100) == 100


def test_cpc_cost_uses_clicks():
    assert cost_for_activation(activation(2), "CPC", 25000, 50) == 100


def test_fx_requires_explicit_non_target_rate():
    assert fx_convert(100, "EUR", "GBP", {"EUR": 0.86}) == 86

    try:
        fx_convert(100, "USD", "GBP", {})
    except ValueError as exc:
        assert "Missing FX rate" in str(exc)
    else:
        raise AssertionError("missing FX rate was silently accepted")
