"""Validation and data-quality reporting for the read-only Notion snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from .models import Activation, Inventory, Product


@dataclass
class DataQualityReport:
    read: dict[str, int] = field(default_factory=dict)
    accepted: dict[str, int] = field(default_factory=dict)
    rejected: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    duplicate_ids: dict[str, tuple[str, ...]] = field(default_factory=dict)
    unresolved_inventory: tuple[str, ...] = ()
    unresolved_products: tuple[str, ...] = ()
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def ok(self) -> bool:
        return not self.issues and not any(self.rejected.values())


def validate_snapshot(
    inventories: Iterable[Inventory],
    activations: Iterable[Activation],
    products: Iterable[Product],
) -> DataQualityReport:
    groups = {
        "inventory": list(inventories),
        "activations": list(activations),
        "products": list(products),
    }
    report = DataQualityReport(read={key: len(rows) for key, rows in groups.items()})
    for key, rows in groups.items():
        ids = [row.id for row in rows]
        duplicates = tuple(sorted({item for item in ids if ids.count(item) > 1}))
        if duplicates:
            report.duplicate_ids[key] = duplicates
            report.issues.append(f"{key}: duplicate IDs {', '.join(duplicates)}")
        valid = 0
        for row in rows:
            problems: list[str] = []
            if not row.id or not row.name:
                problems.append("missing ID or name")
            if isinstance(row, Activation):
                if row.inventory_id is None:
                    problems.append("missing Inventory relation")
                if row.cost is not None and row.cost < 0:
                    problems.append("negative cost")
                for label, value in (
                    ("impressions", row.actual_impressions),
                    ("clicks", row.actual_clicks),
                ):
                    if value is not None and value < 0:
                        problems.append(f"negative {label}")
            if isinstance(row, Product) and (row.ltv is not None and row.ltv < 0):
                problems.append("negative LTV")
            if problems:
                report.issues.append(f"{key} {row.id}: {'; '.join(problems)}")
            else:
                valid += 1
        report.accepted[key] = valid
        report.rejected[key] = len(rows) - valid
    inventory_ids = {row.id for row in groups["inventory"]}
    product_ids = {row.id for row in groups["products"]}
    report.unresolved_inventory = tuple(
        sorted(
            {
                row.inventory_id
                for row in groups["activations"]
                if row.inventory_id and row.inventory_id not in inventory_ids
            }
        )
    )
    report.unresolved_products = tuple(
        sorted(
            {
                row.product_id
                for row in groups["activations"]
                if row.product_id and row.product_id not in product_ids
            }
        )
    )
    for relation, values in (
        ("Inventory", report.unresolved_inventory),
        ("Product", report.unresolved_products),
    ):
        if values:
            report.issues.append(f"unresolved {relation} relations: {', '.join(values)}")
    return report
