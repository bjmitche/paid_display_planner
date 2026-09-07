import streamlit as st

st.set_page_config(page_title="Paid Display Planner", page_icon="📊", layout="wide")

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
    st.write("⏳ Notion read verification")
    st.write("⏳ Campaign simulation")
