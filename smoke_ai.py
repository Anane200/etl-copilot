"""Live smoke test for the Gemini planner and tool-calling executor.

Requires a real GEMINI_API_KEY in .env. The executor step also needs Postgres
running (docker compose up -d postgres).

Run inside the app container:
    docker compose --profile tools run --rm app python smoke_ai.py
"""
from __future__ import annotations

import sys

from agent.executor import ToolCallingExecutor
from agent.planner import AIPlanner
from config.logging_config import setup_logging
from config.settings import Settings
from tools.sql_tool import PostgreSQLConnector


def main() -> int:
    setup_logging()
    settings = Settings.from_env()
    if not settings.gemini_api_key or settings.gemini_api_key == "your_key_here":
        print("GEMINI_API_KEY is not set in .env — cannot run the live smoke test.")
        return 2

    # --- 1. Planner (no DB needed) ---
    print("\n=== Planner ===")
    planner = AIPlanner(settings.gemini_api_key, settings.planner_model)
    plan = planner.plan_etl(
        "Load examples/sample_data.csv into a table called demo, "
        "removing rows with duplicate ids, then report the row count."
    )
    print("Summary:", plan.summary)
    for stage in plan.stages:
        print(f"  - {stage.stage}: {stage.description}")

    # --- 2. Tool-calling executor (needs Postgres) ---
    print("\n=== Executor ===")
    with PostgreSQLConnector(settings.database_url) as connector:
        executor = ToolCallingExecutor(
            settings.gemini_api_key, connector, settings.executor_model
        )
        answer = executor.execute(
            "What tables exist in the database, and how many rows are in each?"
        )
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
