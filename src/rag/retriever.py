"""Retrieve relevant schema documents for a user question."""

from langchain_core.documents import Document

from src.config import Settings
from src.rag.indexer import get_vector_store


def retrieve_relevant_schema(
    question: str,
    settings: Settings,
    top_k: int | None = None,
) -> tuple[list[Document], list[str]]:
    k = top_k or settings.top_k_schema
    vector_store = get_vector_store(settings)
    docs = vector_store.similarity_search(question, k=k)
    table_names = [doc.metadata["table_name"] for doc in docs if "table_name" in doc.metadata]
    return docs, table_names


def format_schema_context(docs: list[Document]) -> str:
    if not docs:
        return "No relevant schema found."
    return "\n\n".join(doc.page_content for doc in docs)
