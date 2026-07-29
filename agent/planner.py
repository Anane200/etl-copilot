"""AI planner: turn a natural-language request into a structured ETL plan.

Uses Gemini's structured-output mode (``response_schema``) so the model returns
schema-validated JSON instead of free text we have to parse and hope is valid.
"""
from __future__ import annotations

import logging

from google import genai
from google.genai import types
from pydantic import BaseModel

from agent.prompts import PLANNER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class StagePlan(BaseModel):
    """One ETL stage: what to do and why."""

    stage: str  # extract | validate | transform | load | report
    description: str


class ETLPlan(BaseModel):
    """A full ordered plan for an ETL request."""

    summary: str
    stages: list[StagePlan]


class AIPlanner:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def plan_etl(self, user_request: str) -> ETLPlan:
        """Break a request into an ordered ETLPlan."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_request,
            config=types.GenerateContentConfig(
                system_instruction=PLANNER_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ETLPlan,
            ),
        )
        # The SDK parses the schema-validated JSON into our pydantic model.
        plan: ETLPlan = response.parsed
        logger.info("Planned %d stage(s): %s", len(plan.stages), plan.summary)
        return plan
