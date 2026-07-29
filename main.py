"""Vertical-slice entrypoint: extract -> validate -> load to Postgres.

Run inside the app container:
    docker compose --profile tools run --rm app python main.py examples/sample_data.csv sample_table
"""
from __future__ import annotations

import logging
import sys

from config.logging_config import setup_logging
from config.settings import Settings
from pipelines.extract import DataReader
from pipelines.load import DataLoader
from pipelines.validate import DataValidator
from tools.sql_tool import PostgreSQLConnector

logger = logging.getLogger(__name__)


def run(file_path: str, table: str) -> dict:
    settings = Settings.from_env()

    df = DataReader(file_path).read()

    validator = DataValidator(df)
    validator.check_no_nulls(list(df.columns))
    validator.check_duplicates()
    report = validator.get_report()
    if not report["is_valid"]:
        logger.error("Validation failed; aborting load: %s", report["errors"])
        return {"status": "failed", "stage": "validate", "errors": report["errors"]}

    with PostgreSQLConnector(settings.database_url) as connector:
        result = DataLoader(connector).load_dataframe(df, table, if_exists="append")
    logger.info("Pipeline result: %s", result)
    return result


def main() -> int:
    setup_logging()
    if len(sys.argv) != 3:
        print("Usage: python main.py <file_path> <table>")
        return 2
    result = run(sys.argv[1], sys.argv[2])
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
