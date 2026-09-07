import os

import pandas as pd
import streamlit as st

from planner.models import (
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


st.title("Paid Display Planner")
st.caption(
    "Campaign-first planning with historical performance expectations and Monte Carlo simulation."
)

with st.sidebar:
    st.header("1. Load campaign data")
    if st.button("Load Campaigns and Activations"):
        try:
            st.session_state["planner_data"] = load_data()
            st.success("Notion data loaded.")
        except Exception as exc:
            st.error(f"Notion load failed: {exc}")

    st.header("MVP status")
    st.write("✅ Notion schema and live read verification")
    st.write("✅ Campaign → Activations loading")
    st.write("✅ Monte Carlo engine")
    st.write("⏳ Production deployment smoke test")

if "planner_data" not in st.session_state:
    st.info("Click **Load Campaigns and Activations** to begin.")
    st.stop()

campaigns, inventories, activations, products = st.session_state["planner_data"]
if not campaigns:
    st.error("No Campaigns were returned from Notion.")
    st.stop()

st.subheader("2. Select campaign")
campaign = st.selectbox("Campaign", campaigns, format_func=lambda item: item.name)
related, missing = (
    [activations[item_id] for item_id in campaign.activation_ids if item_id in activations],
    [item_id for item_id in campaign.activation_ids if item_id not in activations],
)
if missing:
    st.warning(f"{len(missing)} Campaign Activation relation(s) could not be resolved.")
if not related:
    st.warning("This Campaign has no resolvable Activations.")
    st.stop()

activation_labels = {item.id: f"{item.name} ({item.status or 'No status'})" for item in related}
selected_ids = st.multiselect(
    "Activations",
    list(activation_labels),
    default=list(activation_labels),
    format_func=activation_labels.get,
)
selected = [activations[item_id] for item_id in selected_ids]

product = st.selectbox("Product", list(products.values()), format_func=lambda item: item.name)
target_currency = st.selectbox("Target currency", ["EUR", "GBP", "USD"], index=0)
st.caption("Enter FX rates from each non-target source currency into the target currency.")
fx_rates = {
    currency: st.number_input(
        f"{currency} → {target_currency}", min_value=0.000001, value=1.0, key=f"fx_{currency}"
    )
    for currency in ["EUR", "GBP", "USD"]
    if currency != target_currency
}

st.subheader("3. Conversion assumptions")
col1, col2, col3 = st.columns(3)
with col1:
    conv_imp = st.number_input(
        "Conversion / impression", min_value=0.0, value=0.0001, format="%.8f"
    )
with col2:
    conv_view = st.number_input("Conversion / view", min_value=0.0, value=0.001, format="%.8f")
with col3:
    conv_click = st.number_input("Conversion / click", min_value=0.0, value=0.02, format="%.8f")
conv_sigma = st.number_input("Conversion Sigma %", min_value=0.0, value=0.0, format="%.4f")
iterations = st.number_input(
    "Simulation iterations", min_value=100, max_value=10000, value=2000, step=100
)

if st.button("Run simulation", type="primary"):
    input_config = SimulationInputs(
        conv_imp, conv_view, conv_click, conv_sigma, int(iterations), 42, target_currency, fx_rates
    )
    inventory_history = {
        inventory_id: [row for row in activations.values() if row.inventory_id == inventory_id]
        for inventory_id in inventories
    }
    activation_summaries = []
    campaign_rows = []
    for activation in selected:
        inventory = inventories.get(activation.inventory_id)
        if not inventory:
            st.warning(f"Inventory relation missing for {activation.name}.")
            continue
        rows = simulate_activation(
            activation, inventory, inventory_history.get(inventory.id, []), product, input_config
        )
        summary = summarise(rows)
        activation_summaries.append(
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
    if campaign_rows:
        st.subheader("Activation results")
        st.dataframe(pd.DataFrame(activation_summaries), use_container_width=True, hide_index=True)
        st.subheader("Campaign results")
        campaign_summary = summarise(campaign_rows)
        st.dataframe(
            pd.DataFrame(
                [{"Metric": metric, **values} for metric, values in campaign_summary.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )
        chart_data = pd.DataFrame(campaign_rows)[["conversions", "flows", "roi"]]
        st.subheader("Campaign distributions")
        st.line_chart(chart_data)
