"""ETLConfig-driven orchestrator: extract -> validate -> transform -> load.

Ties together the readers, validator, transformer, loader, and (for incremental
pipelines) the watermark store. Produces a ``PipelineRun`` record describing the
outcome for the reporter.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from config.etl_config import ETLConfig
from pipelines.extract import DataReader
from pipelines.load import DataLoader
from pipelines.transform import Transformer
from pipelines.validate import DataValidator
from tools.sql_tool import PostgreSQLConnector
from tools.watermark import WatermarkStore
from utils.retry import with_retry

logger = logging.getLogger(__name__)


@dataclass
class PipelineRun:
    run_id: str
    pipeline_name: str
    start_time: datetime
    end_time: datetime | None = None
    rows_read: int = 0
    rows_loaded: int = 0
    status: str = "running"  # running | success | failed
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        duration = (
            (self.end_time - self.start_time).total_seconds() if self.end_time else None
        )
        return {
            "run_id": self.run_id,
            "pipeline": self.pipeline_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "rows_read": self.rows_read,
            "rows_loaded": self.rows_loaded,
            "status": self.status,
            "errors": self.errors,
        }


def apply_watermark_filter(
    df: pd.DataFrame, column: str, last_value: str | None
) -> pd.DataFrame:
    """Keep only rows strictly greater than the last watermark.

    ``last_value`` is stored as text; it is coerced to the column's dtype so the
    comparison is type-correct for int keys and timestamps alike. A ``None``
    last value (first run) means "take everything".
    """
    if last_value is None:
        return df
    if column not in df.columns:
        raise KeyError(f"Watermark column '{column}' not found in source data")
    typed = pd.Series([last_value]).astype(df[column].dtype).iloc[0]
    filtered = df[df[column] > typed]
    logger.info(
        "Watermark filter on '%s' > %r: %d/%d rows remain",
        column, typed, len(filtered), len(df),
    )
    return filtered


class ETLPipeline:
    def __init__(self, config: ETLConfig, connector: PostgreSQLConnector):
        self.config = config
        self.connector = connector
        self.loader = DataLoader(connector)
        self.watermarks = WatermarkStore(connector)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def run(self) -> PipelineRun:
        cfg = self.config
        run = PipelineRun(
            run_id=uuid.uuid4().hex[:8],
            pipeline_name=cfg.name,
            start_time=self._now(),
        )
        try:
            # --- Extract ---
            df = DataReader(cfg.source.path).read(sheet_name=cfg.source.sheet_name) \
                if cfg.source.type == "excel" else DataReader(cfg.source.path).read()
            run.rows_read = len(df)

            # --- Incremental filter ---
            if cfg.incremental:
                self.watermarks.ensure_table()
                last = self.watermarks.get(cfg.name)
                df = apply_watermark_filter(df, cfg.watermark_column, last)

            # --- Validate ---
            validator = DataValidator(df)
            if cfg.validation.required_columns:
                validator.check_required_columns(cfg.validation.required_columns)
            if cfg.validation.no_nulls:
                validator.check_no_nulls(cfg.validation.no_nulls)
            if cfg.validation.unique:
                validator.check_duplicates(subset=cfg.validation.unique)
            report = validator.get_report()
            if not report["is_valid"]:
                run.status = "failed"
                run.errors = report["errors"]
                run.end_time = self._now()
                logger.error("Validation failed for '%s': %s", cfg.name, run.errors)
                return run

            # --- Transform ---
            df = Transformer(df).apply_config(cfg.transformations).get()

            # --- Load (with retry on transient failures) ---
            load = with_retry(max_attempts=3, base_delay=0.5)(self.loader.load_dataframe)
            result = load(df, cfg.target.table, cfg.target.if_exists)
            if result["status"] != "success":
                run.status = "failed"
                run.errors = [result.get("error", "load failed")]
                run.end_time = self._now()
                return run
            run.rows_loaded = result["rows_loaded"]

            # --- Advance watermark ---
            if cfg.incremental and not df.empty:
                new_wm = df[cfg.watermark_column].max()
                self.watermarks.set(cfg.name, str(new_wm))

            run.status = "success"
        except Exception as e:
            logger.exception("Pipeline '%s' crashed", cfg.name)
            run.status = "failed"
            run.errors = [str(e)]
        finally:
            if run.end_time is None:
                run.end_time = self._now()
        logger.info("Run %s finished: %s", run.run_id, run.status)
        return run
