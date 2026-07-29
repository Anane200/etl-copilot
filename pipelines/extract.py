"""Read source files (CSV / Excel) into pandas DataFrames."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class DataReader:
    """Reads CSV and Excel files from a local path."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.data: pd.DataFrame | None = None

    def read(self, **kwargs) -> pd.DataFrame:
        """Read based on file extension, dispatching to the right engine."""
        suffix = self.file_path.suffix.lower()
        if suffix == ".csv":
            return self.read_csv(**kwargs)
        if suffix in {".xlsx", ".xls"}:
            return self.read_excel(**kwargs)
        raise ValueError(f"Unsupported file type: {suffix!r} ({self.file_path})")

    def read_csv(self, **kwargs) -> pd.DataFrame:
        try:
            self.data = pd.read_csv(self.file_path, **kwargs)
        except Exception:
            logger.exception("Failed to read CSV: %s", self.file_path)
            raise
        logger.info("Read %d rows from %s", len(self.data), self.file_path)
        return self.data

    def read_excel(self, sheet_name: str | int = 0, **kwargs) -> pd.DataFrame:
        try:
            self.data = pd.read_excel(self.file_path, sheet_name=sheet_name, **kwargs)
        except Exception:
            logger.exception("Failed to read Excel: %s", self.file_path)
            raise
        logger.info("Read %d rows from %s", len(self.data), self.file_path)
        return self.data
