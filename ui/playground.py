"""Playground: ask a question or replay an attack, with chosen defenses, and see the trace."""

import os

import httpx
import streamlit as st

from securerag.config import DEFENSES

API = os.environ.get("SECURERAG_API_URL", "http://localhost:8000")
EXAMPLES = [
    "What is the capital of Ghana?",
    "Who was the first President of Ghana?",
    "What is the Ghana Card ID of Ama Mensah, who has an NHIS claim review case?",
]


def call(path: str, payload: dict | None = None):
    r = (
        httpx.post(f"{API}{path}", json=payload, timeout=120)
        if payload
        else httpx.get(f"{API}{path}", timeout=30)
    )
    r.raise_for_status()
    return r.json()


def show(trace: dict) -> None:
    if "attack_succeeded" in trace:
        (st.error if trace["attack_succeeded"] else st.success)(
            "Attack SUCCEEDED" if trace["attack_succeeded"] else "Attack stopped or failed"
        )
    st.markdown(f"**Answer:** {trace['answer']}")
    st.caption(f"{trace['llm_calls']} answer calls, {trace['guard_calls']} Prompt Guard calls")
    if trace["fired"]:
        st.warning(
            "Defenses that fired: " + "; ".join(f"{k}: {v}" for k, v in trace["fired"].items())
        )
    st.markdown("**Retrieved chunks**")
    for c in trace["retrieved"]:
        used = "used" if c["chunk_id"] in trace["used_chunk_ids"] else "dropped"
        with st.expander(f"{c['title']} [{c['trust']}] similarity {c['score']:.2f} ({used})"):
            st.write(c["text"])


st.title("Playground")
defenses = st.multiselect("Defenses", DEFENSES)
tab_q, tab_a = st.tabs(["Ask a question", "Replay an attack"])
with tab_q:
    choice = st.selectbox("Example", ["(type your own)", *EXAMPLES])
    question = st.text_input("Question", "" if choice.startswith("(") else choice)
    if st.button("Ask") and question:
        try:
            show(call("/ask", {"question": question, "defenses": defenses}))
        except httpx.HTTPError as e:
            st.error(f"API error: {e}")
with tab_a:
    try:
        attacks = call("/attacks")
    except httpx.HTTPError as e:
        attacks = []
        st.error(f"API not reachable: {e}")
    kind = st.selectbox("Attack type", sorted({a["kind"] for a in attacks}) or ["-"])
    options = [a for a in attacks if a["kind"] == kind]
    pick = st.selectbox("Attempt", options, format_func=lambda a: f"{a['id']}: {a['query'][:70]}")
    if st.button("Run attack") and pick:
        try:
            show(call("/attack", {"attack_id": pick["id"], "defenses": defenses}))
        except httpx.HTTPError as e:
            st.error(f"API error: {e}")
