"""Collect pipeline run results and emit JSON execution reports."""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PipelineReporter:
    def __init__(self, pipeline_name: str):
        self.pipeline_name = pipeline_name
        self.runs: list[dict] = []

    def add_run(self, run_data: dict) -> None:
        self.runs.append(run_data)

    def get_summary(self) -> dict:
        return {
            "pipeline": self.pipeline_name,
            "total_runs": len(self.runs),
            "successful_runs": sum(1 for r in self.runs if r.get("status") == "success"),
            "total_rows_loaded": sum(r.get("rows_loaded", 0) for r in self.runs),
            "last_run": self.runs[-1] if self.runs else None,
        }

    def save_report(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "pipeline": self.pipeline_name,
            "summary": self.get_summary(),
            "runs": self.runs,
        }
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("Report saved to %s", path)
        return path
