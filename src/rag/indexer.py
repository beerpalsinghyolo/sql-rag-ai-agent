"""Build and refresh the Chroma schema index."""

from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import Settings
from src.db.connection import create_db_engine
from src.db.schema import introspect_schema, schema_to_documents


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def get_vector_store(settings: Settings) -> Chroma:
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection_name(),
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_path,
    )


def index_schema(settings: Settings) -> int:
    engine = create_db_engine(settings)
    tables = introspect_schema(engine)
    documents = schema_to_documents(tables)

    if not documents:
        return 0

    vector_store = get_vector_store(settings)
    collection = vector_store._collection
    existing = collection.get()
    if existing and existing.get("ids"):
        collection.delete(ids=existing["ids"])

    vector_store.add_documents(documents)
    return len(documents)
