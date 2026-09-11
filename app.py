import os

import pandas as pd
import plotly.express as px
import streamlit as st

from planner.economics import ESTIMATOR_VERSION, estimate_inventory
from planner.excel_export import build_workbook
from planner.fx import CURRENCIES, FX_VERSION, fetch_fx_rates
from planner.models import (
    Activation,
    Product,
    normalise_activation,
    normalise_campaign,
    normalise_inventory,
    normalise_product,
)
from planner.notion_client import DEFAULT_DATA_SOURCE_IDS, client_from_values
from planner.simulation import SimulationInputs, simulate_activation, summarise
from planner.validation import validate_snapshot

st.set_page_config(page_title="Paid Display Planner", page_icon="📊", layout="wide")


def setting(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        return os.environ.get(name, default)


def notion_client():
    return client_from_values(
        setting("NOTION_API_TOKEN"),
        campaigns_id=setting("CAMPAIGNS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["campaigns"]),
        inventory_id=setting("INVENTORY_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["inventory"]),
        activations_id=setting(
            "ACTIVATIONS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["activations"]
        ),
        products_id=setting("PRODUCTS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["products"]),
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    client = notion_client()
    campaigns = [normalise_campaign(row) for row in client.query_all("campaigns")]
    inventories = {row["id"]: normalise_inventory(row) for row in client.query_all("inventory")}
    activations = {row["id"]: normalise_activation(row) for row in client.query_all("activations")}
    products = {row["id"]: normalise_product(row) for row in client.query_all("products")}
    quality = validate_snapshot(inventories.values(), activations.values(), products.values())
    return campaigns, inventories, activations, products, quality


def add_scenario_activation(inventory, number: int) -> Activation:
    return Activation(
        f"scenario:{inventory.id}:{number}",
        f"Scenario — {inventory.name} #{number}",
        "Scenario",
        inventory.id,
        None,
        inventory.cost,
        inventory.currency or "EUR",
        None,
        None,
        None,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fx_rates(target_currency: str):
    return fetch_fx_rates(target_currency, CURRENCIES)


st.title("Paid Display Planner")
st.caption(
    "Campaign-first planning. Existing Campaign Activations are the base; added "
    "Inventory rows are scenario-only. "
    f"Build: {ESTIMATOR_VERSION}/{FX_VERSION}"
)

with st.sidebar:
    page = st.radio("Page", ["Planner", "Data quality"], key="page")
    st.header("1. Load campaign data")
    if st.button("Load Campaigns and Activations"):
        try:
            st.session_state["planner_data"] = load_data()
            st.session_state.pop("scenario_activations", None)
            st.session_state.pop("scenario_product_ids", None)
            st.success("Notion data loaded.")
        except Exception as exc:
            st.error(f"Notion load failed: {exc}")
    st.write("✅ Campaign → Activations")
    st.write("✅ Activation-level Products")
    st.write("✅ Scenario Inventory additions")

if "planner_data" not in st.session_state:
    st.info("Click **Load Campaigns and Activations** to begin.")
    st.stop()

campaigns, inventories, activation_map, products, quality = st.session_state["planner_data"]

if page == "Data quality":
    st.title("Data quality")
    st.caption("Read-only validation of the current Notion snapshot and live schema.")
    st.subheader("Snapshot quality")
    st.write({"read": quality.read, "accepted": quality.accepted, "rejected": quality.rejected})
    if quality.issues:
        for issue in quality.issues:
            st.warning(issue)
    else:
        st.success("No snapshot data-quality issues detected.")
    st.subheader("Live Notion schema verification")
    if st.button("Verify Notion data", type="primary"):
        try:
            checks = notion_client().verify()
            for check in checks:
                st.write(f"{'✅' if check.ok else '❌'} {check.key}: {check.row_count} rows")
                if not check.ok:
                    st.warning(
                        f"Missing: {check.missing_properties}; type issues: {check.type_mismatches}"
                    )
        except Exception as exc:
            st.error(f"Notion verification failed: {exc}")
    st.stop()

if not campaigns:
    st.error("No Campaigns were returned from Notion.")
    st.stop()

st.subheader("2. Select campaign")
campaign = st.selectbox("Campaign", campaigns, format_func=lambda item: item.name)
base_ids = [item_id for item_id in campaign.activation_ids if item_id in activation_map]
scenario_activations = st.session_state.setdefault("scenario_activations", [])
all_activation_map = {**activation_map, **{item.id: item for item in scenario_activations}}

st.subheader("3. Add scenario activations")
scenario_inventory = st.selectbox(
    "Add an Inventory item", list(inventories.values()), format_func=lambda item: item.name
)
if st.button("Add Inventory item to scenario"):
    next_number = (
        sum(item.inventory_id == scenario_inventory.id for item in scenario_activations) + 1
    )
    scenario_activations.append(add_scenario_activation(scenario_inventory, next_number))
    st.rerun()

available_ids = base_ids + [item.id for item in scenario_activations]
selected_ids = st.multiselect(
    "Activations included in this scenario",
    available_ids,
    default=available_ids,
    format_func=lambda item_id: all_activation_map[item_id].name,
)
selected = [all_activation_map[item_id] for item_id in selected_ids]

product_options = list(products.values())

st.subheader("4. Product parameters")
scenario_product_ids = st.session_state.setdefault("scenario_product_ids", {})
automatic_product_ids = tuple(
    dict.fromkeys(
        campaign.product_ids + tuple(item.product_id for item in selected if item.product_id)
    )
)
added_product_ids = scenario_product_ids.setdefault(campaign.id, [])
selected_product_ids = list(dict.fromkeys(automatic_product_ids + tuple(added_product_ids)))
product_add_options = [item for item in product_options if item.id not in selected_product_ids]
if product_add_options:
    add_product = st.selectbox(
        "Add a Product to this scenario",
        product_add_options,
        format_func=lambda item: item.name,
        key=f"add_product_{campaign.id}",
    )
    if st.button("Add Product to scenario"):
        added_product_ids.append(add_product.id)
        st.rerun()
else:
    st.caption("All available Products are already selected for this scenario.")
if selected_product_ids:
    st.caption(
        "Selected Products: "
        + ", ".join(products[product_id].name for product_id in selected_product_ids)
    )
product_options = [products[product_id] for product_id in selected_product_ids]
product_names = [item.name for item in product_options]
product_overrides: dict[str, Product] = {}
for product_id in selected_product_ids:
    base_product = products[product_id]
    product_card = st.container(border=True)
    product_card.markdown(f"### {base_product.name}")
    product_card.caption(f"Product economics · {base_product.currency or 'Currency not set'}")
    product_cols = product_card.columns(4)
    with product_cols[0]:
        purchase_amount = st.number_input(
            "Average purchase amount",
            min_value=0.0,
            value=float(base_product.average_purchase_amount or 0.0),
            key=f"product_purchase_{product_id}",
        )
    with product_cols[1]:
        margin_pct = st.number_input(
            "Gross margin (% of assets)",
            min_value=0.0,
            max_value=100.0,
            value=float((base_product.gross_margin_pct or 0.0) * 100),
            key=f"product_margin_{product_id}",
        )
    with product_cols[2]:
        holding_years = st.number_input(
            "Expected holding period (years)",
            min_value=0.0,
            value=float(base_product.holding_period or 0.0),
            key=f"product_holding_{product_id}",
        )
    with product_cols[3]:
        derived_ltv = purchase_amount * (margin_pct / 100) * holding_years
        st.metric("Derived LTV", f"{derived_ltv:,.2f} {base_product.currency or ''}")
    product_overrides[product_id] = Product(
        product_id,
        base_product.name,
        purchase_amount,
        derived_ltv,
        base_product.currency,
        margin_pct / 100,
        holding_years,
    )

st.subheader("5. Activation parameters and Product selection")
history_by_inventory = {
    inventory_id: [row for row in activation_map.values() if row.inventory_id == inventory_id]
    for inventory_id in inventories
}
product_by_activation: dict[str, Product] = {}
conversion_by_activation: dict[str, tuple[float, float, float, float]] = {}
activation_rows = []
edited_activations: dict[str, Activation] = {}
for activation in selected:
    inventory = inventories.get(activation.inventory_id)
    estimate = None
    card = st.container(border=True)
    card.markdown(f"### {activation.name}")
    source_label = (
        "Scenario activation" if activation.id.startswith("scenario:") else "Campaign activation"
    )
    card.caption(
        f"{source_label} · {inventory.name if inventory else 'Inventory relation missing'} "
        f"· {activation.status or 'No status'}"
    )
    cost_cols = card.columns(2)
    inherited_cost = inventory.cost if inventory and inventory.cost is not None else 0.0
    initial_cost = activation.cost if activation.cost is not None else inherited_cost
    with cost_cols[0]:
        activation_cost = st.number_input(
            "Activation Cost / Budget",
            min_value=0.0,
            value=float(initial_cost),
            key=f"activation_cost_{activation.id}",
        )
    with cost_cols[1]:
        activation_currency = st.selectbox(
            "Activation Currency",
            list(CURRENCIES),
            index=(
                list(CURRENCIES).index(activation.currency)
                if activation.currency in CURRENCIES
                else list(CURRENCIES).index(inventory.currency)
                if inventory and inventory.currency in CURRENCIES
                else 0
            ),
            key=f"activation_currency_{activation.id}",
        )
    activation = Activation(
        activation.id,
        activation.name,
        activation.status,
        activation.inventory_id,
        activation.product_id,
        activation_cost,
        activation_currency,
        activation.actual_impressions,
        activation.actual_video_views,
        activation.actual_clicks,
    )
    edited_activations[activation.id] = activation
    if inventory:
        estimate = estimate_inventory(
            inventory,
            history_by_inventory.get(inventory.id, []),
            activation_cost,
        )
        metric_cols = card.columns(4)
        metric_cols[0].metric("Buying model", inventory.buying_model or "Not set")
        metric_cols[1].metric("Rate basis", inventory.rate_basis or "Not set")
        metric_cols[2].metric("Expected impressions", f"{estimate.impressions:,.0f}")
        metric_cols[3].metric("Expected CTR", f"{estimate.ctr * 100:.3f}%")
        card.caption(
            f"Performance estimates: {estimate.method}; "
            f"expected view rate {estimate.view_rate * 100:.3f}%"
        )
        variance_cols = card.columns(4)
        variance_cols[0].metric(
            "Impressions variance",
            f"{estimate.impressions_sigma * 100:.2f}% Sigma",
        )
        variance_cols[1].metric(
            "CTR variance",
            f"{estimate.ctr_sigma * 100:.2f}% Sigma",
        )
    default_product_id = activation.product_id or (
        product_options[0].id if product_options else None
    )
    default_index = next(
        (i for i, item in enumerate(product_options) if item.id == default_product_id), 0
    )
    product_widget_key = f"product_{activation.id}"
    if st.session_state.get(product_widget_key) not in product_names:
        st.session_state.pop(product_widget_key, None)
    chosen_product = card.selectbox(
        f"Product for {activation.name}",
        product_names,
        index=default_index,
        key=f"product_{activation.id}",
    )
    product = product_options[product_names.index(chosen_product)]
    product = product_overrides.get(product.id) or product
    product_by_activation[activation.id] = product
    card.markdown(f"**{activation.name} — conversion assumptions**")
    input_cols = card.columns(4)
    with input_cols[0]:
        imp_pct = st.number_input(
            "Conversion / impression (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.01,
            format="%.4f",
            key=f"imp_{activation.id}",
        )
    with input_cols[1]:
        view_pct = st.number_input(
            "Conversion / view (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.1,
            format="%.4f",
            key=f"view_{activation.id}",
        )
    with input_cols[2]:
        click_pct = st.number_input(
            "Conversion / click (%)",
            min_value=0.0,
            max_value=100.0,
            value=2.0,
            format="%.4f",
            key=f"click_{activation.id}",
        )
    with input_cols[3]:
        sigma_pct = st.number_input(
            "Conversion Sigma (%)",
            min_value=0.0,
            max_value=1000.0,
            value=50.0,
            format="%.4f",
            key=f"sigma_{activation.id}",
        )
    conversion_by_activation[activation.id] = (
        imp_pct / 100,
        view_pct / 100,
        click_pct / 100,
        sigma_pct / 100,
    )
    activation_rows.append(
        {
            "Activation": activation.name,
            "Source": "Scenario" if activation.id.startswith("scenario:") else "Notion Campaign",
            "Inventory": inventory.name if inventory else "Missing",
            "Buying Model": inventory.buying_model if inventory else None,
            "Objective": inventory.objective if inventory else None,
            "Rate Basis": inventory.rate_basis if inventory else None,
            "Cost": activation.cost,
            "Currency": activation.currency,
            "Expected Impressions": estimate.impressions if estimate else None,
            "Expected View Rate": estimate.view_rate if estimate else None,
            "Expected CTR": estimate.ctr if estimate else None,
            "Product": product.name,
        }
    )
st.dataframe(pd.DataFrame(activation_rows), width="stretch", hide_index=True)

if not selected or not product_options:
    st.stop()

st.subheader("5. Campaign assumptions")
target_currency = st.selectbox("Target currency", list(CURRENCIES))
try:
    preloaded_fx_rates, fx_date = cached_fx_rates(target_currency)
    st.caption(
        f"FX rates pre-loaded from Frankfurter/ECB reference rates dated {fx_date}; "
        "values remain editable."
    )
except Exception as exc:
    preloaded_fx_rates = {}
    st.warning(f"Could not pre-load FX rates: {exc}. Enter them manually.")
fx_rates = {
    currency: st.number_input(
        f"{currency} → {target_currency}",
        min_value=0.000001,
        value=preloaded_fx_rates.get(currency, 1.0),
        key=f"fx_{currency}_{target_currency}",
    )
    for currency in CURRENCIES
    if currency != target_currency
}
iterations = st.number_input(
    "Simulation iterations", min_value=100, max_value=10000, value=2000, step=100
)

if st.button("Run simulation", type="primary"):
    history = {
        inventory_id: [row for row in activation_map.values() if row.inventory_id == inventory_id]
        for inventory_id in inventories
    }
    activation_simulations = []
    summaries = []
    for activation in selected:
        edited_activation = edited_activations.get(activation.id)
        if edited_activation is not None:
            activation = edited_activation
        inventory = inventories.get(activation.inventory_id)
        if not inventory:
            continue
        imp_rate, view_rate, click_rate, sigma = conversion_by_activation[activation.id]
        config = SimulationInputs(
            imp_rate,
            view_rate,
            click_rate,
            sigma,
            int(iterations),
            42,
            target_currency,
            fx_rates,
        )
        rows = simulate_activation(
            activation,
            inventory,
            history.get(inventory.id, []),
            product_by_activation[activation.id],
            config,
        )
        summary = summarise(rows)
        estimate = estimate_inventory(
            inventory,
            history.get(inventory.id, []),
            activation.cost,
        )
        summaries.append(
            {
                "Activation": activation.name,
                "Expected impressions": estimate.impressions,
                "Distributed impressions (median)": summary["impressions"]["median"],
                "Engagements (median)": summary["views"]["median"] + summary["clicks"]["median"],
                **{
                    f"{metric} median": values["median"]
                    for metric, values in summary.items()
                    if metric in {"conversions", "flows", "value", "roi"}
                },
            }
        )
        activation_simulations.append((activation, rows))
    campaign_rows = []
    if activation_simulations:
        for index in range(int(iterations)):
            total = {
                metric: sum(rows[index][metric] for _, rows in activation_simulations)
                for metric in (
                    "impressions",
                    "views",
                    "clicks",
                    "conversions",
                    "cost",
                    "flows",
                    "value",
                )
            }
            total["roi"] = total["value"] / total["cost"] if total["cost"] else 0.0
            total["cost_per_conversion"] = (
                total["cost"] / total["conversions"] if total["conversions"] else 0.0
            )
            campaign_rows.append(total)
    st.subheader("Activation results")
    activation_table = pd.DataFrame(summaries)
    activation_integer_columns = {
        "Expected impressions",
        "Distributed impressions (median)",
        "Engagements (median)",
        "conversions median",
    }
    activation_display = activation_table.copy()
    for column in activation_display.columns:
        if column == "Activation":
            continue
        number_format = "{:,.0f}" if column in activation_integer_columns else "{:,.2f}"
        activation_display[column] = activation_display[column].map(
            lambda value: number_format.format(value) if pd.notna(value) else ""
        )
    st.dataframe(activation_display, width="stretch", hide_index=True)
    st.subheader("Campaign results")
    st.caption(
        "Cost per conversion is calculated for each simulation draw as total cost "
        "÷ total conversions. The table ranks outcomes consistently: higher is better "
        "for ROI and value metrics, while lower is better for cost and CAC."
    )
    unit_by_metric = {
        "impressions": "impressions",
        "views": "views",
        "clicks": "clicks",
        "conversions": "conversions",
        "cost": target_currency,
        "flows": target_currency,
        "value": target_currency,
        "roi": "x",
        "cost_per_conversion": f"{target_currency} / conversion",
    }
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
    campaign_summary = summarise(campaign_rows)
    campaign_table = pd.DataFrame(
        [
            {
                "Metric": metric.replace("_", " ").title(),
                "Unit": unit_by_metric.get(metric, ""),
                "Ranking": direction_by_metric[metric],
                "Unfavorable": values["q1"]
                if direction_by_metric[metric] == "Higher is better"
                else values["q3"],
                "Median": values["median"],
                "Favorable": values["q3"]
                if direction_by_metric[metric] == "Higher is better"
                else values["q1"],
            }
            for metric, values in campaign_summary.items()
        ]
    )
    campaign_integer_metrics = {"impressions", "views", "clicks", "conversions"}
    campaign_display = campaign_table.copy()
    for column in ("Unfavorable", "Median", "Favorable"):
        campaign_display[column] = campaign_display[column].astype(object)
    for row_index, metric in enumerate(campaign_summary):
        number_format = "{:,.0f}" if metric in campaign_integer_metrics else "{:,.2f}"
        for column in ("Unfavorable", "Median", "Favorable"):
            campaign_display.loc[row_index, column] = number_format.format(
                campaign_display.loc[row_index, column]
            )
    st.dataframe(campaign_display, width="stretch", hide_index=True)
    campaign_frame = pd.DataFrame(campaign_rows)
    st.subheader("Campaign distributions")
    for metric, title in (("conversions", "Conversions"), ("flows", "Flows"), ("roi", "ROI")):
        figure = px.histogram(campaign_frame, x=metric, title=title)
        if metric == "roi":
            figure.add_vline(x=0, line_dash="dash", line_color="red")
        st.plotly_chart(figure, width="stretch")

    workbook_bytes = build_workbook(
        campaign,
        selected,
        inventories,
        products,
        product_overrides,
        product_by_activation,
        history,
        conversion_by_activation,
        target_currency,
        fx_rates,
        int(iterations),
        activation_simulations,
        campaign_rows,
    )
    st.download_button(
        "Download populated Excel workbook",
        data=workbook_bytes,
        file_name=f"paid_display_planner_{campaign.name[:40].replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
