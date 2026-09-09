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
    target_rate: float = 0.0
    target_rate_sigma: float = 0.0
    target_basis: str | None = None


MIN_DISPERSION = 0.05


def _median(values: list[float]) -> float:
    values = sorted(values)
    n = len(values)
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2


def _cv(values: list[float], fallback: float | None) -> float:
    if len(values) < 2:
        return fallback or 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return fallback or 0.0
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) / mean


def _blended_cv(values: list[float], fallback: float | None) -> float:
    fallback_value = max(fallback or 0.0, 0.0)
    if len(values) < 2:
        return max(fallback_value, MIN_DISPERSION)
    historical = _cv(values, fallback_value)
    weight = min(len(values) / 5.0, 1.0)
    return max((1 - weight) * fallback_value + weight * historical, MIN_DISPERSION)


def _target_fallback(inventory: Inventory) -> tuple[str | None, float, float]:
    basis = (inventory.rate_basis or "").upper()
    if basis == "CPM":
        return (
            basis,
            inventory.expected_cpm or 0.0,
            inventory.cpm_sigma or inventory.impressions_sigma or 0.0,
        )
    if basis == "CPC":
        return basis, inventory.expected_cpc or 0.0, inventory.cpc_sigma or 0.0
    if basis == "CPV":
        return basis, inventory.expected_cpv or 0.0, inventory.cpv_sigma or 0.0
    return None, 0.0, 0.0


def _historical_rate(row: Activation, basis: str) -> float | None:
    if row.cost is None or row.cost < 0:
        return None
    if basis == "CPM" and row.actual_impressions and row.actual_impressions > 0:
        return row.cost / row.actual_impressions * 1000
    if basis == "CPC" and row.actual_clicks and row.actual_clicks > 0:
        return row.cost / row.actual_clicks
    if basis == "CPV" and row.actual_video_views and row.actual_video_views > 0:
        return row.cost / row.actual_video_views
    return None


def estimate_inventory(
    inventory: Inventory,
    history: list[Activation],
    activation_cost: float | None = None,
) -> PerformanceEstimate:
    valid = [
        row
        for row in history
        if (row.status or "").strip().lower() in {"posted", "done", "finished"}
        and row.actual_impressions is not None
        and row.actual_impressions >= 0
    ]
    basis, fallback_rate, fallback_rate_sigma = _target_fallback(inventory)
    rates = [rate for row in valid if basis and (rate := _historical_rate(row, basis)) is not None]
    target_rate = _median(rates) if rates else fallback_rate
    target_sigma = _blended_cv(rates, fallback_rate_sigma) if basis else 0.0

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
    view_rate = (
        min(max(_median(views), 0.0), 1.0)
        if views
        else min(max(inventory.expected_view_rate or 0.0, 0.0), 1.0)
    )
    ctr = (
        min(max(_median(clicks), 0.0), 1.0)
        if clicks
        else min(max(inventory.expected_ctr or 0.0, 0.0), 1.0)
    )
    cost = activation_cost if activation_cost is not None else inventory.cost
    expected_impressions = inventory.expected_impressions or 0.0
    if cost and target_rate > 0 and basis == "CPM":
        expected_impressions = cost / target_rate * 1000
    elif cost and target_rate > 0 and basis == "CPC" and ctr > 0:
        expected_impressions = cost / target_rate / ctr
    elif cost and target_rate > 0 and basis == "CPV" and view_rate > 0:
        expected_impressions = cost / target_rate / view_rate
    elif impressions:
        expected_impressions = _median(impressions)

    return PerformanceEstimate(
        expected_impressions,
        view_rate,
        ctr,
        _blended_cv(impressions, inventory.impressions_sigma),
        _blended_cv(views, inventory.view_rate_sigma),
        _blended_cv(clicks, inventory.ctr_sigma),
        f"historical {basis}" if rates else "fallback",
        target_rate,
        target_sigma,
        basis,
    )


def cost_for_activation(activation: Activation) -> float:
    return max(activation.cost or 0.0, 0.0)


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
