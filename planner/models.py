from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def plain_text(items: list[dict[str, Any]] | None) -> str:
    return "".join(item.get("plain_text", "") for item in items or [])


def prop_value(prop: dict[str, Any] | None) -> Any:
    if not prop:
        return None
    kind = prop.get("type")
    value = prop.get(kind)
    if kind == "title" or kind == "rich_text":
        return plain_text(value)
    if kind == "number":
        return value
    if kind in {"select", "status"}:
        return (value or {}).get("name") if value else None
    if kind == "checkbox":
        return bool(value)
    if kind == "date":
        return (value or {}).get("start") if value else None
    if kind == "relation":
        return [item["id"] for item in value or [] if item.get("id")]
    if kind == "multi_select":
        return [item.get("name") for item in value or []]
    if kind == "formula":
        return prop_value(value if isinstance(value, dict) else None)
    return value


def page_properties(page: dict[str, Any]) -> dict[str, Any]:
    return {name: prop_value(prop) for name, prop in page.get("properties", {}).items()}


@dataclass(frozen=True)
class Campaign:
    id: str
    name: str
    activation_ids: tuple[str, ...]
    stage: str | None
    budget: float | None
    budget_currency: str | None


@dataclass(frozen=True)
class Inventory:
    id: str
    name: str
    format: str | None
    pricing_model: str | None
    expected_cost: float | None
    expected_impressions: float | None
    expected_view_rate: float | None
    expected_ctr: float | None
    impressions_sigma: float | None
    view_rate_sigma: float | None
    ctr_sigma: float | None


@dataclass(frozen=True)
class Activation:
    id: str
    name: str
    status: str | None
    inventory_id: str | None
    product_id: str | None
    cost: float | None
    currency: str | None
    actual_impressions: float | None
    actual_video_views: float | None
    actual_clicks: float | None


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    average_purchase_amount: float | None
    ltv: float | None
    currency: str | None
    gross_margin_pct: float | None = None
    holding_period: float | None = None


def _number(value: Any) -> float | None:
    return float(value) if value is not None else None


def normalise_campaign(page: dict[str, Any]) -> Campaign:
    p = page_properties(page)
    return Campaign(
        page["id"],
        p.get("Campaign name") or p.get("Name") or page["id"],
        tuple(p.get("Activations") or []),
        p.get("Stage"),
        _number(p.get("Budget")),
        p.get("Budget currency"),
    )


def normalise_inventory(page: dict[str, Any]) -> Inventory:
    p = page_properties(page)
    return Inventory(
        page["id"],
        p.get("Name") or page["id"],
        p.get("Format"),
        p.get("Pricing Model"),
        _number(p.get("Expected Cost")),
        _number(p.get("Expected Impressions")),
        _number(p.get("Expected View Rate")),
        _number(p.get("Expected CTR")),
        _number(p.get("Impressions Sigma %")),
        _number(p.get("View Rate Sigma %")),
        _number(p.get("CTR Sigma %")),
    )


def normalise_activation(page: dict[str, Any]) -> Activation:
    p = page_properties(page)
    return Activation(
        page["id"],
        p.get("Name") or page["id"],
        p.get("Status"),
        (p.get("Inventory") or [None])[0],
        (p.get("Product") or [None])[0],
        _number(p.get("Cost")),
        p.get("Currency"),
        _number(p.get("Actual Impressions")),
        _number(p.get("Actual Video Views")),
        _number(p.get("Actual Clicks")),
    )


def normalise_product(page: dict[str, Any]) -> Product:
    p = page_properties(page)
    return Product(
        page["id"],
        p.get("Name") or page["id"],
        _number(p.get("Average Purchase Amount")),
        _number(p.get("LTV")),
        p.get("Value Currency"),
        _number(p.get("Gross Margin %")) or (_number(p.get("Net Margin Bps")) or 0.0) / 10000,
        _number(p.get("Holding Period")),
    )


def resolve_campaign_activations(
    campaign: Campaign, activations: dict[str, Activation]
) -> tuple[list[Activation], list[str]]:
    resolved = [
        activations[activation_id]
        for activation_id in campaign.activation_ids
        if activation_id in activations
    ]
    missing = [
        activation_id
        for activation_id in campaign.activation_ids
        if activation_id not in activations
    ]
    return resolved, missing
