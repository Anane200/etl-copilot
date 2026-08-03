"""Run a config-driven ETL pipeline from a YAML file.

Usage (inside the app container):
    docker compose --profile tools run --rm app \
        python run_pipeline.py examples/sample_pipeline.yaml
"""
from __future__ import annotations

import logging
import sys

from agent.reporter import PipelineReporter
from config.etl_config import ETLConfig
from config.logging_config import setup_logging
from config.settings import Settings
from pipelines.etl_pipeline import ETLPipeline
from tools.sql_tool import PostgreSQLConnector

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    if len(sys.argv) != 2:
        print("Usage: python run_pipeline.py <config.yaml>")
        return 2

    config = ETLConfig.from_yaml(sys.argv[1])
    settings = Settings.from_env()

    with PostgreSQLConnector(settings.database_url) as connector:
        run = ETLPipeline(config, connector).run()

    reporter = PipelineReporter(config.name)
    reporter.add_run(run.to_dict())
    reporter.save_report(f"logs/reports/{config.name}.json")

    print(f"\nRun {run.run_id}: {run.status} "
          f"(read {run.rows_read}, loaded {run.rows_loaded})")
    if run.errors:
        print("Errors:", run.errors)
    return 0 if run.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
