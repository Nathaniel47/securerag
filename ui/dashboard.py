"""Results dashboard: attack success, clean accuracy and false blocks per configuration."""

import streamlit as st

from ui.data import load_results, summary_tables

st.title("Results dashboard")
records = load_results()
if not records:
    st.info("No results yet. Run `python -m securerag.eval.run_eval --mode full`.")
    st.stop()

n_cfg = len({r["config"] for r in records})
st.caption(f"{len(records)} finished queries across {n_cfg} configurations. Rates show k/n.")
t = summary_tables(records)
st.subheader("Attack success rate (lower is better)")
st.dataframe(t["asr"], use_container_width=True)
st.subheader("Clean accuracy, false blocks and cost")
st.dataframe(t["quality"], use_container_width=True)
st.subheader("Security versus usefulness")
st.bar_chart(t["rates"])
