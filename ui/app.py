"""Streamlit entry point: run with `streamlit run ui/app.py`."""

import streamlit as st

st.set_page_config(page_title="SecureRAG", layout="wide")
pages = [
    st.Page("playground.py", title="Playground"),
    st.Page("dashboard.py", title="Results dashboard"),
]
st.navigation(pages).run()
