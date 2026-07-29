# Data Engineering AI Agent

An AI-assisted ETL agent. A **planner** (Gemini) turns a natural-language
request into a structured ETL plan, and a tool-calling **executor** runs real
data-engineering functions (SQL queries, loads) against PostgreSQL.

Everything runs in Docker — nothing is installed on the host.

## Architecture

```
config/      settings + centralised logging
pipelines/   extract (CSV/Excel) -> validate -> load
tools/       sql_tool: pooled, injection-safe Postgres connector
agent/       planner (structured output) + executor (tool calling)
tests/       pytest unit tests
```

The current vertical slice: **extract -> validate -> load to Postgres**, plus a
Gemini planner and a manual tool-calling loop.

## Setup

1. Copy the environment template and fill in values:
   ```bash
   cp .env.example .env
   ```
   Set `GEMINI_API_KEY` for the AI features; `DATABASE_URL` already points at the
   Docker Postgres.

2. Start Postgres:
   ```bash
   docker compose up -d postgres
   ```

## Run the pipeline

```bash
docker compose --profile tools run --rm app \
  python main.py examples/sample_data.csv sample_table
```

## Run the tests

```bash
docker compose --profile tools run --rm app pytest -q
```

The `extract` and `validate` tests need no database or API key. The AI features
require `GEMINI_API_KEY`.

## Design notes

- **SQL injection:** table identifiers are validated against a strict pattern and
  quoted (`tools/sql_tool.py`); values are always bound parameters.
- **Bulk loads:** `load_dataframe` uses pandas multi-row insert, not row-by-row.
- **Structured planning:** the planner uses Gemini `response_schema` so plans are
  schema-validated JSON, not parsed free text.
- **Logging:** configured once on the root logger; modules use
  `getLogger(__name__)`.
