import os

import pandas as pd
import streamlit as st

from planner.fx import CURRENCIES, fetch_fx_rates
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
    return campaigns, inventories, activations, products


def add_scenario_activation(inventory, number: int) -> Activation:
    return Activation(
        f"scenario:{inventory.id}:{number}",
        f"Scenario — {inventory.name} #{number}",
        "Scenario",
        inventory.id,
        None,
        inventory.expected_cost,
        "EUR",
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
    "Inventory rows are scenario-only."
)

with st.sidebar:
    st.header("1. Load campaign data")
    if st.button("Load Campaigns and Activations"):
        try:
            st.session_state["planner_data"] = load_data()
            st.session_state.pop("scenario_activations", None)
            st.success("Notion data loaded.")
        except Exception as exc:
            st.error(f"Notion load failed: {exc}")
    st.write("✅ Campaign → Activations")
    st.write("✅ Activation-level Products")
    st.write("✅ Scenario Inventory additions")

if "planner_data" not in st.session_state:
    st.info("Click **Load Campaigns and Activations** to begin.")
    st.stop()

campaigns, inventories, activation_map, products = st.session_state["planner_data"]
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

st.subheader("4. Activation parameters and Products")
product_options = list(products.values())
product_names = [item.name for item in product_options]
product_by_activation: dict[str, Product] = {}
conversion_by_activation: dict[str, tuple[float, float, float, float]] = {}
activation_rows = []
for activation in selected:
    inventory = inventories.get(activation.inventory_id)
    default_product_id = activation.product_id or (
        product_options[0].id if product_options else None
    )
    default_index = next(
        (i for i, item in enumerate(product_options) if item.id == default_product_id), 0
    )
    chosen_product = st.selectbox(
        f"Product for {activation.name}",
        product_names,
        index=default_index,
        key=f"product_{activation.id}",
    )
    product = product_options[product_names.index(chosen_product)]
    purchase_amount = st.number_input(
        "Average purchase amount",
        min_value=0.0,
        value=float(product.average_purchase_amount or 0.0),
        key=f"purchase_{activation.id}",
    )
    margin_pct = st.number_input(
        "Gross margin (% of assets)",
        min_value=0.0,
        max_value=100.0,
        value=float((product.gross_margin_pct or 0.0) * 100),
        key=f"margin_{activation.id}",
    )
    holding_period = st.number_input(
        "Expected holding period",
        min_value=0.0,
        value=float(product.holding_period or 0.0),
        key=f"holding_{activation.id}",
    )
    holding_unit = st.selectbox(
        "Holding period unit",
        ["Months", "Years"],
        index=0 if product.holding_period_unit == "Months" else 1,
        key=f"holding_unit_{activation.id}",
    )
    holding_years = holding_period / 12 if holding_unit == "Months" else holding_period
    product = Product(
        product.id,
        product.name,
        purchase_amount,
        purchase_amount * (margin_pct / 100) * holding_years,
        product.currency,
        margin_pct / 100,
        holding_period,
        holding_unit,
    )
    product_by_activation[activation.id] = product
    st.markdown(f"**{activation.name} — activation inputs**")
    input_cols = st.columns(4)
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
            value=0.0,
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
            "Pricing Model": inventory.pricing_model if inventory else None,
            "Cost": activation.cost,
            "Currency": activation.currency,
            "Expected Impressions": inventory.expected_impressions if inventory else None,
            "Expected View Rate": inventory.expected_view_rate if inventory else None,
            "Expected CTR": inventory.expected_ctr if inventory else None,
            "Product": product.name,
            "LTV": product.ltv,
            "Average Purchase Amount": product.average_purchase_amount,
            "Product Currency": product.currency,
        }
    )
st.dataframe(pd.DataFrame(activation_rows), use_container_width=True, hide_index=True)

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
    campaign_rows = []
    summaries = []
    for activation in selected:
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
        summaries.append(
            {
                "Activation": activation.name,
                **{
                    f"{metric} median": values["median"]
                    for metric, values in summary.items()
                    if metric in {"conversions", "flows", "value", "roi"}
                },
            }
        )
        campaign_rows.extend(rows)
    st.subheader("Activation results")
    st.dataframe(pd.DataFrame(summaries), use_container_width=True, hide_index=True)
    st.subheader("Campaign results")
    st.dataframe(
        pd.DataFrame(
            [{"Metric": metric, **values} for metric, values in summarise(campaign_rows).items()]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.line_chart(pd.DataFrame(campaign_rows)[["conversions", "flows", "roi"]])
