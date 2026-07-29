"""Application settings loaded from environment (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    gemini_api_key: str | None
    planner_model: str
    executor_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
            )
        return cls(
            database_url=database_url,
            gemini_api_key=os.environ.get("GEMINI_API_KEY"),
            planner_model=os.environ.get("GEMINI_PLANNER_MODEL", "gemini-2.5-flash"),
            executor_model=os.environ.get("GEMINI_EXECUTOR_MODEL", "gemini-2.5-flash"),
        )
