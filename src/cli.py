"""CLI for the SQL RAG agent."""

import typer

from src.agent.sql_agent import SQLRAGAgent
from src.config import get_settings
from src.db.connection import test_connection
from src.rag.indexer import index_schema

app = typer.Typer(help="SQL AI Agent with RAG")


@app.command()
def main(
    reindex: bool = typer.Option(False, "--reindex", help="Rebuild the schema vector index"),
    db: str = typer.Option(None, "--db", help="Database type: sqlite or mysql"),
) -> None:
    settings = get_settings(db_type=db)
    ok, message = test_connection(settings)
    if not ok:
        typer.echo(f"Database connection failed: {message}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Connected to {settings.db_type} database ({settings.db_label()})")

    if reindex:
        count = index_schema(settings)
        typer.echo(f"Indexed {count} table(s) into Chroma.")

    if not settings.groq_api_key:
        typer.echo("Warning: GROQ_API_KEY is not set. Set it in .env before asking questions.", err=True)

    agent = SQLRAGAgent(settings)
    typer.echo("SQL RAG Agent ready. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            question = typer.prompt("You")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nGoodbye!")
            break

        if question.strip().lower() in {"exit", "quit"}:
            typer.echo("Goodbye!")
            break

        if not question.strip():
            continue

        try:
            result = agent.ask(question)
            typer.echo(f"\nAgent: {result['answer']}")
            if result["tables_used"]:
                typer.echo(f"Tables used: {', '.join(result['tables_used'])}")
            if result["sql"]:
                typer.echo(f"SQL: {result['sql']}")
            typer.echo()
        except Exception as exc:
            typer.echo(f"Error: {exc}", err=True)


if __name__ == "__main__":
    app()
