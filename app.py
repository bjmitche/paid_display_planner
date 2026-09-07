import os

import streamlit as st

from planner.notion_client import DEFAULT_DATA_SOURCE_IDS, client_from_values

st.set_page_config(page_title="Paid Display Planner", page_icon="📊", layout="wide")


def configured_value(name: str, default: str) -> str:
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        return os.environ.get(name, default)


st.title("Paid Display Planner")
st.success("Hello from the Paid Display Planner MVP.")
st.write(
    "The Streamlit deployment scaffold is working. Notion integration and campaign "
    "modelling will be added next."
)

with st.sidebar:
    st.header("MVP status")
    st.write("✅ Streamlit app scaffold")
    st.write("✅ Notion data model implemented")
    st.write("✅ Notion schema verification available")
    st.write("⏳ Campaign simulation")

    if st.button("Verify Notion data"):
        try:
            token = configured_value("NOTION_API_TOKEN", "")
            client = client_from_values(
                token,
                inventory_id=configured_value(
                    "INVENTORY_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["inventory"]
                ),
                activations_id=configured_value(
                    "ACTIVATIONS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["activations"]
                ),
                products_id=configured_value(
                    "PRODUCTS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["products"]
                ),
            )
            results = client.verify()
            st.session_state["notion_verification"] = results
        except Exception as exc:  # Streamlit should show the actionable integration error.
            st.error(f"Notion verification failed: {exc}")

verification = st.session_state.get("notion_verification")
if verification:
    st.subheader("Notion data verification")
    if all(result.ok for result in verification):
        st.success("All required Notion schemas and rows were pulled successfully.")
    else:
        st.error("One or more Notion data sources failed verification.")
    st.dataframe(
        [
            {
                "Data source": result.title,
                "Rows pulled": result.row_count,
                "Properties": result.property_count,
                "Missing properties": ", ".join(result.missing_properties) or "None",
                "Type mismatches": ", ".join(result.type_mismatches) or "None",
                "OK": result.ok,
            }
            for result in verification
        ],
        use_container_width=True,
        hide_index=True,
    )
