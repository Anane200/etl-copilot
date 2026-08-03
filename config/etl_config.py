"""Declarative ETL pipeline configuration, loaded from YAML.

A single YAML file fully describes a pipeline: where to read, what to check,
how to transform, where to write, and whether the load is incremental. Using
pydantic gives us validation (unknown fields, wrong types, missing watermark)
at load time rather than deep inside a run.
"""
from __future__ import annotations

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceConfig(BaseModel):
    type: str  # csv | excel
    path: str
    sheet_name: str | int = 0


class TargetConfig(BaseModel):
    type: str = "postgres"
    table: str
    if_exists: str = "append"  # append | replace | fail


class ValidationConfig(BaseModel):
    required_columns: list[str] = Field(default_factory=list)
    no_nulls: list[str] = Field(default_factory=list)
    unique: list[str] = Field(default_factory=list)


class ETLConfig(BaseModel):
    """Top-level pipeline definition. YAML key ``validate`` maps to ``validation``."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    source: SourceConfig
    target: TargetConfig
    validation: ValidationConfig = Field(default_factory=ValidationConfig, alias="validate")
    transformations: list[dict] = Field(default_factory=list)
    incremental: bool = False
    watermark_column: str | None = None

    @model_validator(mode="after")
    def _watermark_required_when_incremental(self) -> "ETLConfig":
        if self.incremental and not self.watermark_column:
            raise ValueError("incremental=true requires 'watermark_column'")
        return self

    @classmethod
    def from_yaml(cls, path: str) -> "ETLConfig":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)
