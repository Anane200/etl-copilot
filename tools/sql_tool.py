"""PostgreSQL connection and query executor built on SQLAlchemy 2.0.

Security notes:
- Query *values* are always passed as bound parameters, never string-formatted.
- Table / schema *identifiers* cannot be bound parameters, so they are validated
  against a strict allow-list pattern and quoted before interpolation. This
  prevents SQL injection through table names (a gap in the original plan code).
"""
from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Postgres unquoted identifiers: letters, digits, underscore; not starting with a digit.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(name: str) -> str:
    """Validate a SQL identifier and return it double-quoted.

    Raises ValueError on anything that isn't a plain identifier, so untrusted
    table names can never break out into arbitrary SQL.
    """
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


class PostgreSQLConnector:
    """Thin wrapper over a pooled SQLAlchemy engine."""

    def __init__(self, connection_string: str, *, pool_size: int = 10, max_overflow: int = 20):
        self.engine: Engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )

    def execute_query(self, query: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute a read query and return rows as dicts."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                rows = [dict(row._mapping) for row in result]
        except Exception:
            logger.exception("Query execution failed")
            raise
        logger.info("Query returned %d rows", len(rows))
        return rows

    def load_dataframe(self, df: pd.DataFrame, table: str, *, if_exists: str = "append") -> int:
        """Bulk-load a DataFrame using pandas' vectorised, multi-row insert.

        Far faster than row-by-row INSERTs. ``if_exists`` is one of
        'append' | 'replace' | 'fail'.
        """
        # Validate identifier early to fail fast with a clear error.
        _safe_identifier(table)
        df.to_sql(
            table,
            self.engine,
            if_exists=if_exists,
            index=False,
            method="multi",
            chunksize=1000,
        )
        logger.info("Loaded %d rows into %s", len(df), table)
        return len(df)

    def table_exists(self, table: str) -> bool:
        _safe_identifier(table)
        return inspect(self.engine).has_table(table)

    def get_row_count(self, table: str) -> int:
        ident = _safe_identifier(table)
        result = self.execute_query(f"SELECT COUNT(*) AS count FROM {ident}")
        return int(result[0]["count"])

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self) -> "PostgreSQLConnector":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
