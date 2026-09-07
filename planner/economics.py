from __future__ import annotations

import math
from dataclasses import dataclass

from .models import Activation, Inventory, Product


@dataclass(frozen=True)
class PerformanceEstimate:
    impressions: float
    view_rate: float
    ctr: float
    impressions_sigma: float
    view_rate_sigma: float
    ctr_sigma: float
    method: str


def _median(values: list[float]) -> float:
    values = sorted(values)
    n = len(values)
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2


def estimate_inventory(inventory: Inventory, history: list[Activation]) -> PerformanceEstimate:
    valid = [
        row
        for row in history
        if row.status in {"Posted", "Done", "Finished"} and row.actual_impressions is not None
    ]
    if not valid:
        return PerformanceEstimate(
            inventory.expected_impressions or 0.0,
            min(max(inventory.expected_view_rate or 0.0, 0.0), 1.0),
            min(max(inventory.expected_ctr or 0.0, 0.0), 1.0),
            inventory.impressions_sigma or 0.0,
            inventory.view_rate_sigma or 0.0,
            inventory.ctr_sigma or 0.0,
            "fallback",
        )
    impressions = [row.actual_impressions for row in valid if row.actual_impressions is not None]
    views = [
        row.actual_video_views / row.actual_impressions
        for row in valid
        if row.actual_video_views is not None and row.actual_impressions
    ]
    clicks = [
        row.actual_clicks / row.actual_impressions
        for row in valid
        if row.actual_clicks is not None and row.actual_impressions
    ]
    return PerformanceEstimate(
        _median(impressions),
        min(max(_median(views), 0.0), 1.0) if views else inventory.expected_view_rate or 0.0,
        min(max(_median(clicks), 0.0), 1.0) if clicks else inventory.expected_ctr or 0.0,
        _cv(impressions, inventory.impressions_sigma),
        _cv(views, inventory.view_rate_sigma),
        _cv(clicks, inventory.ctr_sigma),
        "historical",
    )


def _cv(values: list[float], fallback: float | None) -> float:
    if len(values) < 2:
        return fallback or 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return fallback or 0.0
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) / mean


def cost_for_activation(
    activation: Activation, pricing_model: str | None, impressions: float, clicks: float
) -> float:
    cost = activation.cost or 0.0
    if pricing_model == "CPM":
        return cost * impressions / 1000.0
    if pricing_model == "CPC":
        return cost * clicks
    return cost


def fx_convert(
    amount: float, source_currency: str | None, target_currency: str, rates: dict[str, float]
) -> float:
    if not source_currency or source_currency == target_currency:
        return amount
    if source_currency not in rates:
        raise ValueError(f"Missing FX rate for {source_currency} to {target_currency}.")
    return amount * rates[source_currency]


def product_value(
    product: Product, conversions: float, target_currency: str, rates: dict[str, float]
) -> tuple[float, float]:
    flows = fx_convert(
        conversions * (product.average_purchase_amount or 0.0),
        product.currency,
        target_currency,
        rates,
    )
    value = fx_convert(conversions * (product.ltv or 0.0), product.currency, target_currency, rates)
    return flows, value
