"""Load DataFrames into PostgreSQL and report what happened."""
from __future__ import annotations

import logging

import pandas as pd

from tools.sql_tool import PostgreSQLConnector

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self, connector: PostgreSQLConnector):
        self.connector = connector

    def load_dataframe(self, df: pd.DataFrame, table: str, if_exists: str = "append") -> dict:
        """Load a DataFrame and return a structured result dict."""
        try:
            existed = self.connector.table_exists(table)
            rows_before = self.connector.get_row_count(table) if existed else 0

            self.connector.load_dataframe(df, table, if_exists=if_exists)

            rows_after = self.connector.get_row_count(table)
            rows_loaded = rows_after - rows_before if if_exists == "append" else rows_after

            logger.info("Loaded %d rows into %s", rows_loaded, table)
            return {"status": "success", "rows_loaded": rows_loaded, "table": table}
        except Exception as e:
            logger.exception("Load failed for table %s", table)
            return {"status": "failed", "table": table, "error": str(e)}
