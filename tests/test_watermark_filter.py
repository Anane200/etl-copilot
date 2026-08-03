import pandas as pd
import pytest

from pipelines.etl_pipeline import apply_watermark_filter


@pytest.fixture
def df():
    return pd.DataFrame({"id": [1, 2, 3, 4], "v": ["a", "b", "c", "d"]})


def test_none_watermark_takes_everything(df):
    out = apply_watermark_filter(df, "id", None)
    assert len(out) == 4


def test_filters_rows_above_watermark(df):
    out = apply_watermark_filter(df, "id", "2")   # stored as text, coerced to int
    assert list(out["id"]) == [3, 4]


def test_watermark_at_max_returns_empty(df):
    out = apply_watermark_filter(df, "id", "4")
    assert out.empty


def test_missing_column_raises(df):
    with pytest.raises(KeyError):
        apply_watermark_filter(df, "nope", "1")
