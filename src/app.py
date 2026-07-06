"""Streamlit UI for the SQL RAG agent."""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `from src...` imports work when
# running `streamlit run src/app.py` from the workspace root.
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

import streamlit as st

from src.agent.sql_agent import SQLRAGAgent
from src.config import Settings, get_settings
from src.db.connection import test_connection
from src.rag.indexer import index_schema

st.set_page_config(page_title="SQL RAG Agent", page_icon="🗄️", layout="wide")
st.title("SQL RAG Agent")
st.caption("Ask natural-language questions about your database")


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "db_type" not in st.session_state:
        st.session_state.db_type = "sqlite"


def get_current_settings() -> Settings:
    return get_settings(db_type=st.session_state.db_type)


init_session_state()

with st.sidebar:
    st.header("Settings")
    db_type = st.selectbox(
        "Database",
        options=["sqlite", "mysql"],
        index=0 if st.session_state.db_type == "sqlite" else 1,
    )
    st.session_state.db_type = db_type
    settings = get_current_settings()

    ok, message = test_connection(settings)
    if ok:
        st.success(f"Connected: {settings.db_label()}")
    else:
        st.error(f"Connection failed: {message}")

    if st.button("Reindex schema", use_container_width=True):
        with st.spinner("Indexing schema..."):
            count = index_schema(settings)
        st.success(f"Indexed {count} table(s).")

    st.divider()
    st.markdown("**Example questions**")
    st.markdown(
        "- Which city has the most customers?\n"
        "- What are the top 3 products by price?\n"
        "- Who spent the most on orders?\n"
        "- List all Electronics products"
    )

if not settings.groq_api_key:
    st.warning("Set `GROQ_API_KEY` in your `.env` file to enable the agent.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("meta"):
            with st.expander("Details"):
                if message["meta"].get("tables_used"):
                    st.write("**Tables used:**", ", ".join(message["meta"]["tables_used"]))
                if message["meta"].get("sql"):
                    st.code(message["meta"]["sql"], language="sql")

if prompt := st.chat_input("Ask a question about your data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not settings.groq_api_key:
            response = "Please set GROQ_API_KEY in .env to use the agent."
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        elif not ok:
            response = f"Cannot query — database connection failed: {message}"
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            with st.spinner("Thinking..."):
                try:
                    agent = SQLRAGAgent(settings)
                    result = agent.ask(prompt)
                    st.markdown(result["answer"])
                    meta = {
                        "tables_used": result.get("tables_used", []),
                        "sql": result.get("sql"),
                    }
                    with st.expander("Details"):
                        if meta["tables_used"]:
                            st.write("**Tables used:**", ", ".join(meta["tables_used"]))
                        if meta["sql"]:
                            st.code(meta["sql"], language="sql")
                    st.session_state.messages.append(
                        {"role": "assistant", "content": result["answer"], "meta": meta}
                    )
                except Exception as exc:
                    response = f"Error: {exc}"
                    st.error(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
