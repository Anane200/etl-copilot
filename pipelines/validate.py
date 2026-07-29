"""Data quality validation for pandas DataFrames.

Each ``check_*`` method appends to ``self.errors`` on failure and returns a
bool, so checks can be chained and the accumulated errors reported at the end.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class DataValidator:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.errors: list[str] = []

    def check_required_columns(self, required_cols: list[str]) -> bool:
        missing = set(required_cols) - set(self.df.columns)
        if missing:
            self.errors.append(f"Missing columns: {sorted(missing)}")
            return False
        return True

    def check_no_nulls(self, columns: list[str]) -> bool:
        ok = True
        for col in columns:
            if col not in self.df.columns:
                self.errors.append(f"Cannot null-check missing column: '{col}'")
                ok = False
                continue
            count = int(self.df[col].isnull().sum())
            if count:
                self.errors.append(f"Column '{col}' has {count} null values")
                ok = False
        return ok

    def check_duplicates(self, subset: list[str] | None = None) -> bool:
        dups = int(self.df.duplicated(subset=subset).sum())
        if dups:
            self.errors.append(f"Found {dups} duplicate rows")
            return False
        return True

    def check_data_types(self, type_map: dict[str, str]) -> bool:
        ok = True
        for col, expected in type_map.items():
            if col not in self.df.columns:
                self.errors.append(f"Cannot type-check missing column: '{col}'")
                ok = False
                continue
            actual = str(self.df[col].dtype)
            if not actual.startswith(expected):
                self.errors.append(
                    f"Column '{col}' type mismatch: expected {expected!r}, got {actual!r}"
                )
                ok = False
        return ok

    def get_report(self) -> dict:
        report = {
            "rows_total": len(self.df),
            "columns": len(self.df.columns),
            "errors": list(self.errors),
            "is_valid": len(self.errors) == 0,
        }
        if report["is_valid"]:
            logger.info("Validation passed (%d rows)", report["rows_total"])
        else:
            logger.warning("Validation failed: %s", report["errors"])
        return report
