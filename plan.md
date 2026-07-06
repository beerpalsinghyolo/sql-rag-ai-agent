# SQL AI Agent with RAG
Build a project that uses LangChain, Groq, and open-source RAG (Chroma + HuggingFace embeddings) to answer natural-language questions over SQLite or MySQL, with both a CLI and Streamlit UI.

## Table of Contents

- [Goal](#goal)
- [Quick start guide](#quick-start-guide)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Layout](#project-layout)
- [Key Implementation Details](#key-implementation-details)
- [Example User Flow](#example-user-flow)
- [Future Scope (next version)](#future-scope-next-version)
- [Risks and Mitigations](#risks-and-mitigations)

## Goal

1. Connects to **SQLite** (local demo) or **MySQL** (production)
2. Uses **RAG** to retrieve only relevant schema chunks (instead of dumping the full schema)
3. Uses **Groq** as the LLM via `langchain-groq`
4. Exposes a **CLI** and **Streamlit** chat interface

## Quick start guide

### 1. Setup
- Create a virtual environment and install dependencies:
  `pip install -r requirements.txt`
- Copy `.env.example` to `.env` and add your `GROQ_API_KEY`.
- Seed the demo SQLite database:
  `python scripts/seed_sqlite.py`

### 2. Build the schema index
- Reindex once before first use:
  `python -m src.cli --reindex`

### 3. Run the app
- CLI:
  `python -m src.cli`
- Streamlit UI:
  `streamlit run src/app.py`

## Architecture

```mermaid
flowchart LR
    User[UserQuestion] --> UI[CLI_or_Streamlit]
    UI --> Retriever[SchemaRAGRetriever]
    Retriever --> Chroma[ChromaDB]
    Chroma --> SchemaDocs[TableColumnDocs]
    Retriever --> Agent[LangChainSQLAgent]
    Agent --> Groq[GroqLLM]
    Agent --> DB[(SQLite_or_MySQL)]
    DB --> Agent
    Agent --> Answer[NaturalLanguageAnswer]
```

**RAG vs naive SQL agent:** LangChain’s default SQL toolkit sends the entire schema to the LLM. For multi-table databases this is slow and error-prone. We will embed each table (name, columns, types, optional description) as a document, retrieve top-k relevant tables for the user question, and pass only that subset to the agent.

## Tech Stack

| Layer        | Choice                                                                                   |
| ------------ | ---------------------------------------------------------------------------------------- |
| LLM          | Groq (`llama-3.3-70b-versatile` or `llama-3.1-8b-instant`) via `langchain-groq`          |
| Embeddings   | `sentence-transformers/all-MiniLM-L6-v2` via `langchain-huggingface` (local, no API key) |
| Vector store | ChromaDB (`langchain-chroma`) persisted under `./chroma_db/`                             |
| DB access    | SQLAlchemy + LangChain `SQLDatabase`                                                     |
| CLI          | `typer` or simple `input()` loop                                                         |
| UI           | Streamlit                                                                                |


## Project Layout

```
./
├── .gitignore
├── .env.example
├── README.md
├── plan.md
├── requirements.txt
├── scripts/
│   └── seed_sqlite.py          # creates demo SQLite with sample tables
├── src/
│   ├── __init__.py
│   ├── config.py               # pydantic-settings: DB type, URLs, Groq key
│   ├── db/
│   │   ├── connection.py         # SQLAlchemy URI builder (sqlite/mysql)
│   │   └── schema.py             # introspect tables/columns → Document chunks
│   ├── rag/
│   │   ├── indexer.py            # build/refresh Chroma index from schema
│   │   └── retriever.py          # similarity search → relevant schema text
│   ├── agent/
│   │   └── sql_agent.py          # create agent with RAG-filtered schema
│   ├── cli.py                    # terminal chat loop
│   └── app.py                    # Streamlit UI
├── data/
│   └── demo.db                 # seeded SQLite sample
└── chroma_db/
```

## Key Implementation Details

### 1. Configuration — `[src/config.py](src/config.py)`

Use `pydantic-settings` to load from `.env`:

```python
DB_TYPE=sqlite          # sqlite | mysql
SQLITE_PATH=./data/demo.db
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=mydb
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
TOP_K_SCHEMA=5
```

Build SQLAlchemy URI:

- SQLite: `sqlite:///./data/demo.db`
- MySQL: `mysql+pymysql://user:pass@host:3306/db`

### 2. Sample SQLite database — `[scripts/seed_sqlite.py](scripts/seed_sqlite.py)`

Seed a small **e-commerce demo** (easy to query, no external deps):

- `customers` (id, name, email, city)
- `products` (id, name, category, price)
- `orders` (id, customer_id, order_date, total)
- `order_items` (order_id, product_id, quantity)

Insert ~20–30 rows so example questions work out of the box (“top customers by spend”, “products in Electronics”, etc.).

### 3. Schema RAG — `[src/rag/](src/rag/)`

**Indexing** (`[indexer.py](src/rag/indexer.py)`):

- Call `SQLDatabase.get_table_info_no_throw()` or SQLAlchemy inspector
- For each table, create a document like:

```
Table: orders
Columns: id INTEGER PK, customer_id INTEGER FK→customers.id, order_date DATE, total DECIMAL
Description: Customer purchase records
Sample values: customer_id references customers
```

- Embed with HuggingFace, store in Chroma collection `schema_{db_name}`
- Refresh index when DB changes (CLI flag `--reindex`)

**Retrieval** (`[retriever.py](src/rag/retriever.py)`):

- On each user question, retrieve top `TOP_K_SCHEMA` table docs
- Format as `relevant_schema` string injected into agent system prompt

### 4. SQL Agent — `[src/agent/sql_agent.py](src/agent/sql_agent.py)`

Use LangChain’s SQL toolkit:

```python
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq

db = SQLDatabase.from_uri(uri, include_tables=retrieved_table_names)
llm = ChatGroq(model=settings.groq_model, temperature=0)
agent = create_sql_agent(
    llm=llm,
    db=db,
    agent_type="tool-calling",
    verbose=True,
    prefix=SYSTEM_PROMPT_WITH_RAG_SCHEMA,
)
```

**System prompt additions:**

- Only use retrieved tables unless a JOIN requires a related table
- Generate read-only `SELECT` queries (no `DROP`, `DELETE`, `UPDATE`)
- If unsure, ask a clarifying question
- Always inspect query results before answering

**Safety:** Set `SQLDatabase` with `sample_rows_in_table_info=2` for context, and optionally wrap execution to reject non-SELECT statements.

### 5. CLI — `[src/cli.py](src/cli.py)`

```
python -m src.cli
python -m src.cli --reindex
python -m src.cli --db mysql
```

Loop: read question → RAG retrieve → agent invoke → print answer + generated SQL (from intermediate steps if verbose).

### 6. Streamlit UI — `[src/app.py](src/app.py)`

- Sidebar: DB selector (SQLite demo / MySQL), connection status, “Reindex schema” button
- Main: chat history (`st.chat_message`), input box
- Show expandable “Generated SQL” and “Tables used” per response
- Run with: `streamlit run src/app.py`

### 7. Dependencies — `[requirements.txt](requirements.txt)`

```
langchain>=0.3
langchain-community
langchain-groq
langchain-chroma
langchain-huggingface
chromadb
sqlalchemy
pymysql
pydantic-settings
python-dotenv
streamlit
typer
sentence-transformers
```

## Example User Flow

1. `python scripts/seed_sqlite.py` — create demo DB
2. Copy `.env.example` → `.env`, add `GROQ_API_KEY`
3. `python -m src.cli --reindex` — build schema index
4. Ask: *“Which city has the most customers?”*
5. Agent retrieves `customers` table schema → generates `SELECT city, COUNT(*) ...` → returns answer


## Future Scope (next version)

- Auth / multi-user sessions
- Query result caching
- Fine-tuned models
- Automatic chart generation
- Production deployment (Docker/K8s)

## Risks and Mitigations


| Risk                         | Mitigation                                                       |
| ---------------------------- | ---------------------------------------------------------------- |
| Groq rate limits             | Default to `llama-3.1-8b-instant` for dev; document model choice |
| Wrong table retrieved        | Increase `TOP_K_SCHEMA`; include FK hints in schema docs         |
| Destructive SQL              | Prompt guardrails + optional SELECT-only validator               |
| First-run embedding download | Document ~90MB model download for sentence-transformers          |


