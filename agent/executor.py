"""Tool-calling executor: let Gemini invoke real data-engineering functions.

This is a manual function-calling loop (rather than the SDK's automatic mode)
so we stay in control of dispatch, logging, and the iteration guard. Tools are
registered as name -> (declaration, python callable); the loop feeds each
function result back to the model until it stops requesting tools.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from google import genai
from google.genai import types

from agent.prompts import EXECUTOR_SYSTEM_PROMPT
from tools.sql_tool import PostgreSQLConnector

logger = logging.getLogger(__name__)

# Guard against a model that keeps calling tools without ever finishing.
MAX_ITERATIONS = 10


class ToolCallingExecutor:
    def __init__(
        self,
        api_key: str,
        connector: PostgreSQLConnector,
        model: str = "gemini-2.5-flash",
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.connector = connector
        self._handlers: dict[str, Callable[..., Any]] = {
            "run_sql_query": self._run_sql_query,
            "get_row_count": self._get_row_count,
            "list_tables": self._list_tables,
            "run_etl_pipeline": self._run_etl_pipeline,
        }
        self._tools = types.Tool(function_declarations=self._declarations())

    # --- Tool implementations -------------------------------------------------
    def _run_sql_query(self, query: str) -> list[dict]:
        return self.connector.execute_query(query)

    def _get_row_count(self, table: str) -> dict:
        return {"table": table, "count": self.connector.get_row_count(table)}

    def _list_tables(self) -> dict:
        return {"tables": self.connector.list_tables()}

    def _run_etl_pipeline(self, config_path: str) -> dict:
        """Run a config-driven ETL pipeline defined in a YAML file."""
        # Imported here to keep the agent layer decoupled from the pipeline
        # layer at module load time.
        from config.etl_config import ETLConfig
        from pipelines.etl_pipeline import ETLPipeline

        config = ETLConfig.from_yaml(config_path)
        run = ETLPipeline(config, self.connector).run()
        return run.to_dict()

    # --- Tool declarations exposed to the model -------------------------------
    @staticmethod
    def _declarations() -> list[types.FunctionDeclaration]:
        return [
            types.FunctionDeclaration(
                name="run_sql_query",
                description="Execute a read-only SQL SELECT query and return rows.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="A single SQL SELECT statement.",
                        )
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_row_count",
                description="Return the number of rows in a table.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "table": types.Schema(
                            type=types.Type.STRING,
                            description="Table name.",
                        )
                    },
                    required=["table"],
                ),
            ),
            types.FunctionDeclaration(
                name="list_tables",
                description="List the names of all tables in the database.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={}),
            ),
            types.FunctionDeclaration(
                name="run_etl_pipeline",
                description=(
                    "Run a config-driven ETL pipeline defined in a YAML file "
                    "(extract, validate, transform, load) and return the run "
                    "summary including rows read/loaded and status."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "config_path": types.Schema(
                            type=types.Type.STRING,
                            description="Path to the pipeline YAML config file.",
                        )
                    },
                    required=["config_path"],
                ),
            ),
        ]

    def _dispatch(self, name: str, args: dict) -> Any:
        handler = self._handlers.get(name)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return handler(**args)
        except Exception as e:  # surface tool errors back to the model
            logger.exception("Tool %s failed", name)
            return {"error": str(e)}

    # --- Main loop ------------------------------------------------------------
    def execute(self, user_request: str) -> str:
        config = types.GenerateContentConfig(
            system_instruction=EXECUTOR_SYSTEM_PROMPT,
            tools=[self._tools],
        )
        contents: list[types.Content] = [
            types.Content(role="user", parts=[types.Part(text=user_request)])
        ]

        for _ in range(MAX_ITERATIONS):
            response = self.client.models.generate_content(
                model=self.model, contents=contents, config=config
            )
            parts = response.candidates[0].content.parts or []
            calls = [p.function_call for p in parts if p.function_call]

            if not calls:
                return response.text or ""

            # Record the model's tool-request turn, then answer each call.
            contents.append(response.candidates[0].content)
            for call in calls:
                result = self._dispatch(call.name, dict(call.args or {}))
                logger.info("Executed tool %s", call.name)
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=call.name, response={"result": result}
                            )
                        ],
                    )
                )

        logger.warning("Reached MAX_ITERATIONS (%d) without completion", MAX_ITERATIONS)
        return "Stopped: reached the maximum number of tool-calling iterations."
