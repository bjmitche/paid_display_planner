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

    def __post_init__(self) -> None:
        if self.iterations < 1:
            raise ValueError("iterations must be positive")
        for value in (
            self.conversion_per_impression,
            self.conversion_per_view,
            self.conversion_per_click,
        ):
            if value < 0 or value > 1:
                raise ValueError("conversion rates must be between 0 and 1")


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
        views = impressions * view_rate if "video" in (inventory.format or "").lower() else 0.0
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


def simulate_campaign(
    activations: list[Activation],
    inventories: dict[str, Inventory],
    history: dict[str, list[Activation]],
    products: dict[str, Product],
    inputs_by_activation: dict[str, SimulationInputs],
) -> tuple[dict[str, list[dict[str, float]]], list[dict[str, float]]]:
    """Simulate selected activations and aggregate totals per iteration."""
    activation_rows: dict[str, list[dict[str, float]]] = {}
    for activation in activations:
        inventory = inventories.get(activation.inventory_id or "")
        product = products.get(activation.product_id or "")
        if not inventory or not product:
            continue
        activation_rows[activation.id] = simulate_activation(
            activation,
            inventory,
            history.get(inventory.id, []),
            product,
            inputs_by_activation[activation.id],
        )
    if not activation_rows:
        return activation_rows, []
    iterations = min(len(rows) for rows in activation_rows.values())
    campaign: list[dict[str, float]] = []
    for index in range(iterations):
        total = {key: sum(rows[index][key] for rows in activation_rows.values()) for key in (
            "impressions", "views", "clicks", "conversions", "cost", "flows", "value"
        )}
        total["roi"] = total["value"] / total["cost"] if total["cost"] else 0.0
        total["cost_per_conversion"] = (
            total["cost"] / total["conversions"] if total["conversions"] else 0.0
        )
        campaign.append(total)
    return activation_rows, campaign


def summarise(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    if not rows:
        return {}
    result: dict[str, dict[str, float]] = {}
    for key in rows[0]:
        values = sorted(row[key] for row in rows)
        q1, q3 = (
            quantiles(values, n=4, method="inclusive")[0],
            quantiles(values, n=4, method="inclusive")[2],
        )
        result[key] = {"q1": q1, "median": values[len(values) // 2], "q3": q3}
    return result
