"""Offline tests for the tool-calling executor's dispatch and declarations.

These never call Gemini: the client is constructed with a dummy key (no network
happens until generate_content) and tools are exercised via _dispatch directly.
"""
import pytest

from agent.executor import ToolCallingExecutor


class FakeConnector:
    def execute_query(self, query):
        return [{"result": 1}]

    def get_row_count(self, table):
        return 42

    def list_tables(self):
        return ["alpha", "beta"]


@pytest.fixture
def executor():
    return ToolCallingExecutor(api_key="test-key", connector=FakeConnector())


def test_declarations_match_handlers(executor):
    declared = {d.name for d in executor._tools.function_declarations}
    assert declared == set(executor._handlers)


def test_dispatch_routes_to_handlers(executor):
    assert executor._dispatch("get_row_count", {"table": "t"}) == {"table": "t", "count": 42}
    assert executor._dispatch("list_tables", {}) == {"tables": ["alpha", "beta"]}
    assert executor._dispatch("run_sql_query", {"query": "SELECT 1"}) == [{"result": 1}]


def test_dispatch_unknown_tool_returns_error(executor):
    out = executor._dispatch("does_not_exist", {})
    assert "error" in out


def test_dispatch_surfaces_handler_exception(executor):
    # A missing config file makes ETLConfig.from_yaml raise; the loop must
    # surface it as an error result rather than crashing.
    out = executor._dispatch("run_etl_pipeline", {"config_path": "no_such_file.yaml"})
    assert "error" in out
