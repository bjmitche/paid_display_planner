from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import quantiles

from .economics import cost_for_activation, estimate_inventory, fx_convert, product_value
from .models import Activation, Inventory, Product


@dataclass(frozen=True)
class SimulationInputs:
    conversion_per_impression: float
    conversion_per_view: float
    conversion_per_click: float
    conversion_sigma: float = 0.0
    iterations: int = 2000
    seed: int = 42
    target_currency: str = "EUR"
    fx_rates: dict[str, float] | None = None


def _draw_positive(median: float, cv: float, rng: random.Random) -> float:
    if median <= 0:
        return 0.0
    sigma = math.sqrt(math.log(1 + max(cv, 0.0) ** 2))
    mu = math.log(median) - sigma * sigma / 2
    return rng.lognormvariate(mu, sigma) if sigma else median


def _draw_rate(value: float, cv: float, rng: random.Random) -> float:
    return min(max(_draw_positive(value, cv, rng), 0.0), 1.0)


def simulate_activation(
    activation: Activation,
    inventory: Inventory,
    history: list[Activation],
    product: Product,
    inputs: SimulationInputs,
) -> list[dict[str, float]]:
    estimate = estimate_inventory(inventory, history)
    rates = inputs.fx_rates or {}
    rng = random.Random(inputs.seed)
    output: list[dict[str, float]] = []
    for _ in range(inputs.iterations):
        impressions = _draw_positive(estimate.impressions, estimate.impressions_sigma, rng)
        view_rate = _draw_rate(estimate.view_rate, estimate.view_rate_sigma, rng)
        ctr = _draw_rate(estimate.ctr, estimate.ctr_sigma, rng)
        views = impressions * view_rate
        clicks = impressions * ctr
        imp_rate = _draw_rate(inputs.conversion_per_impression, inputs.conversion_sigma, rng)
        view_rate_conversion = _draw_rate(inputs.conversion_per_view, inputs.conversion_sigma, rng)
        click_rate = _draw_rate(inputs.conversion_per_click, inputs.conversion_sigma, rng)
        conversions = impressions * imp_rate + views * view_rate_conversion + clicks * click_rate
        cost = cost_for_activation(activation, inventory.pricing_model, impressions, clicks)
        cost = fx_convert(cost, activation.currency, inputs.target_currency, rates)
        flows, value = product_value(product, conversions, inputs.target_currency, rates)
        output.append(
            {
                "impressions": impressions,
                "views": views,
                "clicks": clicks,
                "conversions": conversions,
                "cost": cost,
                "flows": flows,
                "value": value,
                "roi": value / cost if cost else 0.0,
            }
        )
    return output


def summarise(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for key in rows[0]:
        values = sorted(row[key] for row in rows)
        q1, q3 = (
            quantiles(values, n=4, method="inclusive")[0],
            quantiles(values, n=4, method="inclusive")[2],
        )
        result[key] = {"q1": q1, "median": values[len(values) // 2], "q3": q3}
    return result
