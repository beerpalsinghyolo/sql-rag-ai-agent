"""LangChain SQL agent with RAG-filtered schema context."""

import re

from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq

from src.config import Settings
from src.db.connection import get_sql_database
from src.rag.retriever import format_schema_context, retrieve_relevant_schema

SYSTEM_PROMPT_TEMPLATE = """You are a helpful SQL assistant. Answer questions by querying the database.

IMPORTANT RULES:
- Only generate read-only SELECT queries. Never use INSERT, UPDATE, DELETE, DROP, or ALTER.
- Use only the tables listed below unless a JOIN requires a directly related table.
- Always run a query to verify results before answering.
- If the question is ambiguous, state your assumptions.
- Format answers clearly with the relevant numbers or names from query results.

RELEVANT SCHEMA (retrieved via RAG):
{schema_context}
"""


def _extract_sql_from_steps(steps: list) -> str | None:
    for step in reversed(steps):
        if not isinstance(step, tuple) or len(step) < 2:
            continue
        action, _ = step[0], step[1]
        tool_input = getattr(action, "tool_input", None)
        if isinstance(tool_input, dict):
            query = tool_input.get("query", "")
        else:
            query = str(tool_input or "")
        query = query.strip()
        if query.upper().startswith("SELECT"):
            return query
    return None


def _extract_sql_from_output(output: str) -> str | None:
    match = re.search(r"```sql\s*(SELECT[\s\S]*?)```", output, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(SELECT[\s\S]+?;)", output, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


class SQLRAGAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = ChatGroq(
            model=settings.groq_model,
            groq_api_key=settings.groq_api_key,
            temperature=0,
        )

    def ask(self, question: str) -> dict:
        schema_docs, table_names = retrieve_relevant_schema(question, self.settings)
        schema_context = format_schema_context(schema_docs)

        db = get_sql_database(
            self.settings,
            include_tables=table_names or None,
        )

        prefix = SYSTEM_PROMPT_TEMPLATE.format(schema_context=schema_context)
        agent = create_sql_agent(
            llm=self.llm,
            db=db,
            agent_type="tool-calling",
            verbose=False,
            prefix=prefix,
        )

        try:
            result = agent.invoke({"input": question})
        except Exception as exc:
            message = str(exc)
            if "model_permission_blocked_project" in message or "blocked at the project level" in message:
                raise RuntimeError(
                    "Groq model permission error: the selected model is blocked for your project. "
                    "Set GROQ_MODEL in .env to a model enabled for your project, or enable the current model in Groq project settings."
                ) from exc
            raise

        output = result.get("output", str(result))
        intermediate_steps = result.get("intermediate_steps", [])

        sql = _extract_sql_from_steps(intermediate_steps) or _extract_sql_from_output(output)

        return {
            "answer": output,
            "sql": sql,
            "tables_used": table_names,
            "schema_context": schema_context,
        }
