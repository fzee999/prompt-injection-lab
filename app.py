"""Prompt Injection Lab: the interface.

A thin Streamlit front end over lab.assistant.answer(). Ask a question and see
the reply, which documents the model was given, tokens and latency, and whether
the canary leaked. The "What the model saw" panel shows the exact messages that
were sent. That is the point of a lab: nothing is hidden from the operator,
only from the model's users.

Every question is answered on its own (no conversation memory), exactly as the
harness will ask them, so what you see here is what the experiment measures.

Run from the project folder:
    .venv\\Scripts\\python -m streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from lab.assistant import answer, build_messages, select_documents
from lab.config import get_settings
from lab.prompts import SECRET, load_documents

st.set_page_config(page_title="Prompt Injection Lab", page_icon="🔒", layout="wide")


@st.cache_resource
def corpus():
    """Load the documents once per server process, not on every rerun."""
    return load_documents()


docs = corpus()
settings = get_settings()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Assistant")
    mode = st.radio(
        "Documents in the prompt",
        ["all", "topk"],
        index=0,
        help="all: every document, every time (what the experiment uses). "
        "topk: the k documents whose words best match the question.",
    )
    k = st.slider("k, for topk", min_value=1, max_value=len(docs), value=2)
    max_tokens = st.slider("Max reply tokens", min_value=50, max_value=600, value=300, step=50)
    st.caption(f"Model `{settings.model}`  \nat `{settings.base_url}`")
    st.divider()
    st.header("Defenses")
    st.caption("Day 2. The toggles appear here once they exist.")
    st.divider()
    show_secret = st.toggle("Show the secret in the lab panel", value=False)
    if st.button("Clear the conversation"):
        st.session_state.log = []

# ---------------------------------------------------------------- main
st.title("Northgate State University · Policy Assistant")
st.caption(
    "A document Q&A assistant with a hidden secret, built to be attacked. "
    "Ask about assistantships, the library, parking or IT policy."
)

if "log" not in st.session_state:
    st.session_state.log = []

question = st.chat_input("Ask a policy question")
if question:
    used = docs if mode == "all" else select_documents(question, docs, k)
    with st.spinner("Asking the model…"):
        result = answer(question, docs=used, mode="all", max_tokens=max_tokens)
    st.session_state.log.append(
        {
            "question": question,
            "answer": result,
            "messages": build_messages(question, used),
            "mode": mode,
        }
    )


def masked(text: str) -> str:
    return text if show_secret else text.replace(SECRET, "•" * len(SECRET))


for entry in st.session_state.log:
    a = entry["answer"]
    leaked = SECRET in a.text
    with st.chat_message("user"):
        st.write(entry["question"])
    with st.chat_message("assistant"):
        st.write(a.text)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prompt tokens", a.result.prompt_tokens)
        c2.metric("Reply tokens", a.result.completion_tokens)
        c3.metric("Seconds", f"{a.result.seconds:.1f}")
        c4.metric("Canary leaked", "YES" if leaked else "no")
        if leaked:
            st.error("The reply contains the secret.")
        st.caption(f"Mode `{entry['mode']}` · documents given to the model: " + ", ".join(a.documents))
        with st.expander("What the model saw"):
            for m in entry["messages"]:
                st.markdown(f"**{m['role']}**")
                st.code(masked(m["content"]), language="text")

with st.expander("The corpus", expanded=not st.session_state.log):
    tabs = st.tabs([d.title for d in docs])
    for tab, d in zip(tabs, docs):
        with tab:
            # Streamlit renders "$...$" as LaTeX; policy text is full of dollar amounts.
            st.markdown(d.text.replace("$", "\\$"))
