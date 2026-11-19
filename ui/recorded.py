"""Recorded runs: replay any stored attack or question under every defense, no API calls."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from ui.data import load_results, replay_rows

records = load_results()
attacks = [json.loads(line) for line in Path("data/attacks.jsonl").read_text("utf-8").splitlines()]
questions = [
    json.loads(line) for line in Path("data/questions.jsonl").read_text("utf-8").splitlines()
]

st.title("Recorded runs")
st.caption(
    "Every attack and question was run once under each defense setting. Pick one to see what "
    "each setting answered. These are stored results, so nothing here uses the live quota."
)
if not records:
    st.info("No recorded results are available.")
    st.stop()

kind = st.radio(
    "Show", ["poisoning", "indirect_injection", "direct_injection", "leakage", "clean"],
    horizontal=True,
)  # fmt: skip
if kind == "clean":
    items = {q["id"]: q["question"] for q in questions}
else:
    items = {a["id"]: a["query"] for a in attacks if a["kind"] == kind}
pick = st.selectbox("Example", list(items), format_func=lambda i: f"{i}: {items[i][:80]}")
st.markdown(f"**Question sent:** {items[pick]}")
rows = replay_rows(records, pick)
if kind == "clean":
    label = {True: "correct", False: "wrong"}
else:
    label = {True: "ATTACK SUCCEEDED", False: "attack stopped"}
frame = pd.DataFrame(rows)
frame["outcome"] = frame["outcome"].map(label)
st.dataframe(frame, use_container_width=True, hide_index=True)
