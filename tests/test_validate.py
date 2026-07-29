import pandas as pd
import pytest

from pipelines.validate import DataValidator


@pytest.fixture
def good_df():
    return pd.DataFrame(
        {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "amount": [100.0, 200.0, 300.0]}
    )


def test_valid_data_passes(good_df):
    v = DataValidator(good_df)
    assert v.check_required_columns(["id", "name", "amount"])
    assert v.check_no_nulls(["id"])
    assert v.check_duplicates()
    report = v.get_report()
    assert report["is_valid"]
    assert report["errors"] == []


def test_bad_data_accumulates_all_errors():
    df = pd.DataFrame({"id": [1, 1, 3], "name": ["Alice", None, "Charlie"]})
    v = DataValidator(df)
    assert not v.check_duplicates()          # duplicate id row
    assert not v.check_no_nulls(["name"])    # null name
    report = v.get_report()
    assert not report["is_valid"]
    # Both problems surfaced, not just the first.
    assert len(report["errors"]) == 2


def test_missing_column_is_reported_not_raised():
    v = DataValidator(pd.DataFrame({"id": [1]}))
    assert not v.check_no_nulls(["does_not_exist"])
    assert any("does_not_exist" in e for e in v.errors)
