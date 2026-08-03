"""Persist per-pipeline watermarks in Postgres for incremental loads.

Stores the highest processed value of each pipeline's watermark column so the
next run only picks up newer rows. Values are kept as text (portable across
int / timestamp watermark columns) and coerced back at compare time.
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from tools.sql_tool import PostgreSQLConnector

logger = logging.getLogger(__name__)

_TABLE = "etl_watermarks"


class WatermarkStore:
    def __init__(self, connector: PostgreSQLConnector):
        self.connector = connector

    def ensure_table(self) -> None:
        """Create the watermark table if it does not exist (idempotent)."""
        ddl = f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                pipeline_name   TEXT PRIMARY KEY,
                watermark_value TEXT NOT NULL,
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """
        with self.connector.engine.begin() as conn:
            conn.execute(text(ddl))

    def get(self, pipeline_name: str) -> str | None:
        rows = self.connector.execute_query(
            f"SELECT watermark_value FROM {_TABLE} WHERE pipeline_name = :name",
            {"name": pipeline_name},
        )
        return rows[0]["watermark_value"] if rows else None

    def set(self, pipeline_name: str, value: str) -> None:
        """Upsert the watermark for a pipeline."""
        stmt = text(
            f"""
            INSERT INTO {_TABLE} (pipeline_name, watermark_value, updated_at)
            VALUES (:name, :value, now())
            ON CONFLICT (pipeline_name)
            DO UPDATE SET watermark_value = EXCLUDED.watermark_value,
                          updated_at = now()
            """
        )
        with self.connector.engine.begin() as conn:
            conn.execute(stmt, {"name": pipeline_name, "value": str(value)})
        logger.info("Watermark for '%s' set to %s", pipeline_name, value)
