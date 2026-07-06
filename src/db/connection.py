"""Database connection utilities."""

from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from src.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(settings.sqlalchemy_uri())


def test_connection(settings: Settings) -> tuple[bool, str]:
    try:
        engine = create_db_engine(settings)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connected"
    except SQLAlchemyError as exc:
        return False, str(exc)


def get_sql_database(
    settings: Settings,
    include_tables: list[str] | None = None,
    sample_rows: int = 2,
) -> SQLDatabase:
    return SQLDatabase.from_uri(
        settings.sqlalchemy_uri(),
        include_tables=include_tables,
        sample_rows_in_table_info=sample_rows,
    )
