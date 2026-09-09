from __future__ import annotations

import math
from copy import copy
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from .economics import estimate_inventory
from .models import Activation, Campaign, Inventory, Product

TEMPLATE_PATH = Path(__file__).parents[1] / "templates" / "Paid_Display_Planner_Template.xlsx"


def _copy_row_style(sheet, source_row: int, target_row: int, max_column: int) -> None:
    for column in range(1, max_column + 1):
        source = sheet.cell(source_row, column)
        target = sheet.cell(target_row, column)
        if source.has_style:
            target._style = copy(source._style)
        if source.number_format:
            target.number_format = source.number_format
    sheet.row_dimensions[target_row].height = sheet.row_dimensions[source_row].height


def _write_rows(
    sheet, start_row: int, rows: list[list[Any]], template_row: int, max_column: int
) -> None:
    for offset, values in enumerate(rows):
        row = start_row + offset
        if row != template_row:
            _copy_row_style(sheet, template_row, row, max_column)
        for column, value in enumerate(values, 1):
            sheet.cell(row, column).value = value


def _replace_table(sheet, old_name: str, new_name: str, ref: str) -> None:
    if old_name in sheet.tables:
        del sheet.tables[old_name]
    table = Table(displayName=new_name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    sheet.add_table(table)


def _clear_data(sheet, start_row: int, end_row: int, max_column: int) -> None:
    for row in range(start_row, end_row + 1):
        for column in range(1, max_column + 1):
            sheet.cell(row, column).value = None


def _histogram(values: list[float], bins: int = 20) -> list[tuple[float, float, int]]:
    if not values:
        return [(0.0, 1.0, 0)] * bins
    low = min(values)
    high = max(values)
    width = (high - low) / bins if high > low else 1.0
    counts = [0] * bins
    for value in values:
        index = min(bins - 1, math.floor((value - low) / width))
        counts[index] += 1
    return [(low + width * i, low + width * (i + 1), counts[i]) for i in range(bins)]


def _quartile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction) - 1))
    return ordered[index]


def build_workbook(
    campaign: Campaign,
    selected: list[Activation],
    inventories: dict[str, Inventory],
    products: dict[str, Product],
    product_overrides: dict[str, Product],
    history_by_inventory: dict[str, list[Activation]],
    conversion_by_activation: dict[str, tuple[float, float, float, float]],
    target_currency: str,
    fx_rates: dict[str, float],
    iterations: int,
    activation_simulations: list[tuple[Activation, list[dict[str, float]]]],
    campaign_rows: list[dict[str, float]],
) -> bytes:
    workbook = load_workbook(TEMPLATE_PATH)
    inputs = workbook["Model Inputs & Assumptions"]
    summary = workbook["Performance Summary"]
    activation_detail = workbook["Activation Detail"]
    simulation_detail = workbook["Simulation Detail"]

    inputs["C5"] = campaign.name
    inputs["C6"] = "Streamlit scenario"
    inputs["C7"] = date.today()
    inputs["C8"] = target_currency
    inputs["C9"] = iterations
    inputs["C10"] = 42
    inputs["C12"] = "Exported from Paid Display Planner. Values are a read-only scenario snapshot."

    selected_inventory_ids = list(
        dict.fromkeys(item.inventory_id for item in selected if item.inventory_id)
    )
    relevant_inventories = [
        inventories[inventory_id]
        for inventory_id in selected_inventory_ids
        if inventory_id in inventories
    ]
    inventory_rows = []
    for inventory in relevant_inventories:
        history = history_by_inventory.get(inventory.id, [])
        estimate = estimate_inventory(inventory, history)
        inventory_rows.append(
            [
                inventory.id,
                inventory.name,
                estimate.method,
                len(history),
                sum(a.actual_impressions is not None for a in history),
                sum(a.actual_video_views is not None for a in history),
                sum(a.actual_clicks is not None for a in history),
                estimate.impressions,
                sum(a.actual_impressions or 0 for a in history),
                sum(a.actual_video_views or 0 for a in history),
                sum(a.actual_clicks or 0 for a in history),
                estimate.view_rate,
                estimate.ctr,
                inventory.expected_impressions or 0,
                inventory.expected_view_rate or 0,
                inventory.expected_ctr or 0,
                inventory.impressions_sigma or 0,
                inventory.view_rate_sigma or 0,
                inventory.ctr_sigma or 0,
                estimate.impressions,
                estimate.view_rate,
                estimate.ctr,
                estimate.impressions,
                estimate.view_rate,
                estimate.ctr,
                estimate.method,
                "Exported historical/fallback estimate",
            ]
        )

    product_rows = []
    for product in {p.id: p for p in product_overrides.values()}.values():
        product_rows.append(
            [
                product.id,
                product.name,
                product.currency,
                product.average_purchase_amount or 0,
                product.gross_margin_pct or 0,
                product.holding_period or 0,
                product.ltv or 0,
                fx_rates.get(product.currency or target_currency, 1.0),
                "Loaded from Notion with any Streamlit override applied.",
            ]
        )

    activation_rows = []
    for activation in selected:
        inventory = inventories.get(activation.inventory_id or "")
        product = product_overrides.get(activation.product_id or "") or products.get(
            activation.product_id or ""
        )
        estimate = (
            estimate_inventory(inventory, history_by_inventory.get(inventory.id, []))
            if inventory
            else None
        )
        imp, view, click, sigma = conversion_by_activation[activation.id]
        activation_rows.append(
            [
                activation.id,
                activation.name,
                "Scenario activation"
                if activation.id.startswith("scenario:")
                else "Campaign activation",
                inventory.id if inventory else None,
                inventory.name if inventory else None,
                inventory.format if inventory else None,
                activation.status,
                inventory.buying_model if inventory else None,
                activation.cost,
                activation.currency,
                fx_rates.get(activation.currency or target_currency, 1.0),
                product.id if product else None,
                product.name if product else None,
                imp,
                view,
                click,
                sigma,
                estimate.method if estimate else "Unavailable",
                estimate.impressions if estimate else None,
                estimate.impressions_sigma if estimate else None,
                estimate.view_rate if estimate else None,
                estimate.view_rate_sigma if estimate else None,
                estimate.ctr if estimate else None,
                estimate.ctr_sigma if estimate else None,
                "Exported scenario input.",
            ]
        )

    fx_rows = [
        [
            target_currency,
            target_currency,
            1.0,
            "Planner target currency",
            date.today(),
            "No",
            "Identity rate",
        ]
    ]
    fx_rows.extend(
        [
            currency,
            target_currency,
            rate,
            "Frankfurter/ECB preload",
            date.today(),
            "No",
            "Editable source rate",
        ]
        for currency, rate in fx_rates.items()
    )

    for start, capacity, count, insert_at in (
        (52, 0, len(fx_rows), 52),
        (44, 3, len(product_rows), 44),
        (37, 8, len(activation_rows), 37),
        (25, 7, len(inventory_rows), 25),
    ):
        if count > capacity:
            inputs.insert_rows(insert_at, count - capacity)

    _clear_data(inputs, 17, 23, 27)
    _clear_data(inputs, 28, 35, 25)
    _clear_data(inputs, 40, 42, 9)
    _clear_data(inputs, 47, 50, 7)
    _write_rows(inputs, 17, inventory_rows, 17, 27)
    _write_rows(inputs, 28, activation_rows, 28, 25)
    _write_rows(inputs, 40, product_rows, 40, 9)
    _write_rows(inputs, 47, fx_rows, 47, 7)
    inputs.tables["InventoryEstimates"].ref = f"A16:AA{16 + len(inventory_rows)}"
    inputs.tables["Activations"].ref = f"A27:Y{27 + len(activation_rows)}"
    inputs.tables["Products"].ref = f"A39:I{39 + len(product_rows)}"
    inputs.tables["FXRates"].ref = f"A46:G{46 + len(fx_rows)}"

    activation_headers = [
        "Activation ID",
        "Activation",
        "Source",
        "Inventory",
        "Product",
        "Status",
        "Pricing model",
        "Cost",
        "Currency",
        "Expected impressions",
        "Expected view rate %",
        "Expected CTR %",
        "Conv / impression %",
        "Conv / view %",
        "Conv / click %",
        "Conversion Sigma %",
        "Actual impressions",
        "Actual video views",
        "Actual clicks",
        "Actual view rate %",
        "Actual CTR %",
        "Sim impressions Q1",
        "Sim impressions median",
        "Sim impressions Q3",
        "Sim views median",
        "Sim clicks median",
        "Sim engagements median",
        "Sim conversions Q1",
        "Sim conversions median",
        "Sim conversions Q3",
        "Sim flows median",
        "Sim LTV median",
        "Sim cost median",
        "Sim ROI median",
        "Estimation method",
    ]
    activation_summary_rows = []
    for activation, rows in activation_simulations:
        inventory = inventories.get(activation.inventory_id or "")
        product = product_overrides.get(activation.product_id or "") or products.get(
            activation.product_id or ""
        )
        estimate = (
            estimate_inventory(inventory, history_by_inventory.get(inventory.id, []))
            if inventory
            else None
        )
        imp, view, click, sigma = conversion_by_activation[activation.id]
        activation_summary_rows.append(
            [
                activation.id,
                activation.name,
                "Scenario activation"
                if activation.id.startswith("scenario:")
                else "Campaign activation",
                inventory.name if inventory else None,
                product.name if product else None,
                activation.status,
                inventory.buying_model if inventory else None,
                activation.cost,
                activation.currency,
                estimate.impressions if estimate else None,
                estimate.view_rate if estimate else None,
                estimate.ctr if estimate else None,
                imp,
                view,
                click,
                sigma,
                activation.actual_impressions,
                activation.actual_video_views,
                activation.actual_clicks,
                activation.actual_video_views / activation.actual_impressions
                if activation.actual_video_views is not None and activation.actual_impressions
                else None,
                activation.actual_clicks / activation.actual_impressions
                if activation.actual_clicks is not None and activation.actual_impressions
                else None,
                _quartile([r["impressions"] for r in rows], 0.25),
                _quartile([r["impressions"] for r in rows], 0.50),
                _quartile([r["impressions"] for r in rows], 0.75),
                _quartile([r["views"] for r in rows], 0.50),
                _quartile([r["clicks"] for r in rows], 0.50),
                _quartile([r["views"] + r["clicks"] for r in rows], 0.50),
                _quartile([r["conversions"] for r in rows], 0.25),
                _quartile([r["conversions"] for r in rows], 0.50),
                _quartile([r["conversions"] for r in rows], 0.75),
                _quartile([r["flows"] for r in rows], 0.50),
                _quartile([r["value"] for r in rows], 0.50),
                _quartile([r["cost"] for r in rows], 0.50),
                _quartile([r["roi"] for r in rows], 0.50),
                estimate.method if estimate else "Unavailable",
            ]
        )
    _clear_data(activation_detail, 3, activation_detail.max_row, 35)
    _write_rows(activation_detail, 3, [activation_headers] + activation_summary_rows, 3, 35)
    _replace_table(
        activation_detail,
        "ActivationDetail",
        "ActivationSummary",
        f"A3:AI{3 + len(activation_summary_rows)}",
    )

    simulation_headers = ["Metric", "Unit", "Ex-post", "Q1", "Median", "Q3", "Definition"]
    ex_post = {
        "impressions": sum(a.actual_impressions or 0 for a in selected),
        "views": sum(a.actual_video_views or 0 for a in selected),
        "clicks": sum(a.actual_clicks or 0 for a in selected),
    }
    simulation_rows = []
    for label, key, unit, definition in (
        ("Impressions", "impressions", "count", "Distributed impressions"),
        ("Views", "views", "count", "Recorded video views"),
        ("Clicks", "clicks", "count", "Recorded clicks"),
        ("Conversions", "conversions", "count", "Simulation conversion output"),
        ("Flows", "flows", target_currency, "Conversions × average purchase amount"),
        ("Cost", "cost", target_currency, "Deterministic fixed, CPM or CPC cost"),
        ("LTV value", "value", target_currency, "Conversions × derived LTV"),
        ("ROI", "roi", "x", "LTV value ÷ cost"),
    ):
        values = [row[key] for row in campaign_rows] if campaign_rows else []
        simulation_rows.append(
            [
                label,
                unit,
                ex_post.get(key),
                _quartile(values, 0.25),
                _quartile(values, 0.50),
                _quartile(values, 0.75),
                definition,
            ]
        )
    _clear_data(simulation_detail, 3, simulation_detail.max_row, 12)
    _write_rows(simulation_detail, 3, [simulation_headers] + simulation_rows, 3, 7)
    _replace_table(
        simulation_detail,
        "SimulationDetail",
        "SimulationSummary",
        f"A3:G{3 + len(simulation_rows)}",
    )

    summary["B5"] = campaign.name
    summary["B6"] = "Streamlit scenario"
    summary["B7"] = target_currency
    summary["B8"] = len(selected)
    summary["B9"] = len(product_overrides)
    summary["B10"] = iterations
    campaign_metrics = {
        "Impressions": "impressions",
        "Video views": "views",
        "Clicks": "clicks",
        "Conversions": "conversions",
        "Flows": "flows",
        "Cost": "cost",
        "Cost per conversion": "cost_per_conversion",
        "LTV value": "value",
        "ROI": "roi",
    }
    summary["B14"] = "Unfavorable"
    summary["C14"] = "Median"
    summary["D14"] = "Favorable"
    direction_by_metric = {
        "impressions": "Higher is better",
        "views": "Higher is better",
        "clicks": "Higher is better",
        "conversions": "Higher is better",
        "cost": "Lower is better",
        "flows": "Higher is better",
        "value": "Higher is better",
        "roi": "Higher is better",
        "cost_per_conversion": "Lower is better",
    }
    for row, (label, key) in enumerate(campaign_metrics.items(), 15):
        values = sorted(item[key] for item in campaign_rows) if campaign_rows else [0]
        q1 = values[max(0, int(len(values) * 0.25) - 1)]
        q3 = values[max(0, int(len(values) * 0.75) - 1)]
        summary.cell(row, 1).value = label
        summary.cell(row, 2).value = q1 if direction_by_metric[key] == "Higher is better" else q3
        summary.cell(row, 3).value = _quartile(values, 0.50)
        summary.cell(row, 4).value = q3 if direction_by_metric[key] == "Higher is better" else q1
        unit = (
            target_currency
            if key in {"cost", "flows", "value", "cost_per_conversion"}
            else "x"
            if key == "roi"
            else "count"
        )
        summary.cell(row, 5).value = f"{direction_by_metric[key]}; unit: {unit}"

    for summary_row, metric in ((24, "LTV value"), (25, "ROI")):
        for column, statistic in ((2, "D"), (3, "E"), (4, "F")):
            summary.cell(summary_row, column).value = (
                f"=INDEX('Simulation Detail'!${statistic}:${statistic},"
                f"MATCH(\"{metric}\",'Simulation Detail'!$A:$A,0))"
            )

    if len(activation_simulations) > 8:
        summary.insert_rows(37, len(activation_simulations) - 8)
    activation_summary_rows = []
    for activation, rows in activation_simulations:
        inventory = inventories.get(activation.inventory_id or "")
        product = product_overrides.get(activation.product_id or "") or products.get(
            activation.product_id or ""
        )
        estimate = (
            estimate_inventory(inventory, history_by_inventory.get(inventory.id, []))
            if inventory
            else None
        )
        activation_summary_rows.append(
            [
                activation.name,
                "Scenario activation"
                if activation.id.startswith("scenario:")
                else "Campaign activation",
                inventory.name if inventory else None,
                product.name if product else None,
                estimate.method if estimate else "Unavailable",
                estimate.impressions if estimate else None,
                estimate.view_rate if estimate else None,
                estimate.ctr if estimate else None,
                _quartile([r["conversions"] for r in rows], 0.50),
                _quartile([r["conversions"] for r in rows], 0.25),
                _quartile([r["conversions"] for r in rows], 0.75),
                _quartile([r["flows"] for r in rows], 0.50),
                _quartile([r["value"] for r in rows], 0.50),
                _quartile([r["cost"] for r in rows], 0.50),
                _quartile([r["roi"] for r in rows], 0.50),
                _quartile(
                    [r["cost"] / r["conversions"] if r["conversions"] else 0 for r in rows],
                    0.50,
                ),
            ]
        )
    _clear_data(summary, 29, 36 + max(0, len(activation_simulations) - 8), 16)
    _write_rows(summary, 29, activation_summary_rows, 29, 16)
    conversion_bins = _histogram([row["conversions"] for row in campaign_rows])
    roi_bins = _histogram([row["roi"] for row in campaign_rows])
    summary["A83"] = (
        "Fixed histogram bins: 20 equal-width bins per distribution; "
        "final bin includes the maximum."
    )
    for offset, (start, end, count) in enumerate(conversion_bins, 85):
        summary.cell(offset, 1).value = start
        summary.cell(offset, 2).value = end
        summary.cell(offset, 3).value = f"{start:,.2f}"
        summary.cell(offset, 4).value = count
    for offset, (start, end, count) in enumerate(roi_bins, 85):
        summary.cell(offset, 6).value = start
        summary.cell(offset, 7).value = end
        summary.cell(offset, 8).value = f"{start:,.2f}"
        summary.cell(offset, 9).value = count

    output = BytesIO()
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.save(output)
    return output.getvalue()
