"""Chainable, config-driven DataFrame transformations.

Methods return ``self`` so calls chain fluently, and ``apply_config`` drives the
same operations from a list of ``{"op": ..., ...}`` dicts (the transformations
block of an ETLConfig). Only whitelisted ops are dispatchable.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class Transformer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def remove_duplicates(self, subset: list[str] | None = None) -> "Transformer":
        before = len(self.df)
        self.df = self.df.drop_duplicates(subset=subset)
        logger.info("Removed %d duplicate rows", before - len(self.df))
        return self

    def fill_nulls(self, column: str, value: Any) -> "Transformer":
        self.df[column] = self.df[column].fillna(value)
        logger.info("Filled nulls in '%s' with %r", column, value)
        return self

    def rename_columns(self, mapping: dict[str, str]) -> "Transformer":
        self.df = self.df.rename(columns=mapping)
        logger.info("Renamed columns: %s", mapping)
        return self

    def drop_columns(self, columns: list[str]) -> "Transformer":
        self.df = self.df.drop(columns=columns)
        logger.info("Dropped columns: %s", columns)
        return self

    def cast(self, column: str, dtype: str) -> "Transformer":
        self.df[column] = self.df[column].astype(dtype)
        logger.info("Cast '%s' to %s", column, dtype)
        return self

    # Whitelist of ops that apply_config is allowed to dispatch.
    _DISPATCH = {"remove_duplicates", "fill_nulls", "rename_columns", "drop_columns", "cast"}

    def apply_config(self, steps: list[dict]) -> "Transformer":
        """Apply an ordered list of transformation steps from config."""
        for step in steps:
            params = dict(step)
            op = params.pop("op", None)
            if op not in self._DISPATCH:
                raise ValueError(f"Unknown or unsupported transformation op: {op!r}")
            getattr(self, op)(**params)
        return self

    def get(self) -> pd.DataFrame:
        return self.df
