import pandas as pd
import pytest

from pipelines.transform import Transformer


@pytest.fixture
def df():
    # The two id=2 rows are full-row duplicates (identical incl. the null).
    return pd.DataFrame(
        {"id": [1, 2, 2], "name": ["a", "b", "b"], "amount": [10.0, None, None]}
    )


def test_chaining_returns_self_and_transforms(df):
    out = (
        Transformer(df)
        .remove_duplicates()
        .fill_nulls("amount", 0)
        .rename_columns({"amount": "total"})
        .get()
    )
    assert len(out) == 2                      # one dup row removed
    assert "total" in out.columns
    assert out["total"].isnull().sum() == 0


def test_does_not_mutate_input(df):
    Transformer(df).fill_nulls("amount", 0)
    assert df["amount"].isnull().sum() == 2   # original untouched


def test_apply_config_dispatches_ops(df):
    steps = [
        {"op": "remove_duplicates"},
        {"op": "rename_columns", "mapping": {"name": "label"}},
        {"op": "drop_columns", "columns": ["amount"]},
    ]
    out = Transformer(df).apply_config(steps).get()
    assert "label" in out.columns
    assert "amount" not in out.columns


def test_apply_config_rejects_unknown_op(df):
    with pytest.raises(ValueError):
        Transformer(df).apply_config([{"op": "delete_everything"}])
