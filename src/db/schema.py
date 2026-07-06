"""Schema introspection and document generation for RAG indexing."""

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from langchain_core.documents import Document

TABLE_DESCRIPTIONS: dict[str, str] = {
    "customers": "Customer profiles with contact and location information.",
    "products": "Product catalog with category and pricing.",
    "orders": "Customer purchase records with order date and total amount.",
    "order_items": "Line items linking orders to products with quantities.",
}


def _format_column(col: dict) -> str:
    parts = [col["name"], col["type"]]
    if col.get("primary_key"):
        parts.append("PK")
    if col.get("foreign_keys"):
        fk_targets = ", ".join(
            f"{fk['referred_table']}.{fk['referred_columns'][0]}"
            for fk in col["foreign_keys"]
        )
        parts.append(f"FK→{fk_targets}")
    if not col.get("nullable", True):
        parts.append("NOT NULL")
    return " ".join(parts)


def introspect_schema(engine: Engine) -> list[dict]:
    inspector = inspect(engine)
    tables = []

    for table_name in inspector.get_table_names():
        columns = []
        pk = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
        fks = inspector.get_foreign_keys(table_name)

        fk_map: dict[str, list[dict]] = {}
        for fk in fks:
            for local_col, referred_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                fk_map.setdefault(local_col, []).append(
                    {
                        "referred_table": fk["referred_table"],
                        "referred_columns": [referred_col],
                    }
                )

        for col in inspector.get_columns(table_name):
            col_name = col["name"]
            col_type = str(col["type"])
            columns.append(
                {
                    "name": col_name,
                    "type": col_type,
                    "nullable": col.get("nullable", True),
                    "primary_key": col_name in pk,
                    "foreign_keys": fk_map.get(col_name, []),
                }
            )

        tables.append({"name": table_name, "columns": columns})

    return tables


def schema_to_documents(tables: list[dict]) -> list[Document]:
    documents = []
    for table in tables:
        table_name = table["name"]
        column_lines = [_format_column(col) for col in table["columns"]]
        description = TABLE_DESCRIPTIONS.get(table_name, f"Database table {table_name}.")

        content = (
            f"Table: {table_name}\n"
            f"Description: {description}\n"
            f"Columns: {', '.join(column_lines)}"
        )

        documents.append(
            Document(
                page_content=content,
                metadata={"table_name": table_name},
            )
        )
    return documents


def get_all_table_names(engine: Engine) -> list[str]:
    return inspect(engine).get_table_names()
