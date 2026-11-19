"""Streamlit entry point: run with `streamlit run ui/app.py`."""

import streamlit as st

st.set_page_config(page_title="SecureRAG", layout="wide")
pages = [
    st.Page("dashboard.py", title="Results dashboard"),
    st.Page("recorded.py", title="Recorded runs"),
    st.Page("playground.py", title="Live playground"),
]
st.navigation(pages).run()
