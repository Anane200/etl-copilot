import pandas as pd
import pytest

from pipelines.extract import DataReader


@pytest.fixture
def sample_csv(tmp_path):
    csv_file = tmp_path / "sample.csv"
    pd.DataFrame(
        {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "value": [100, 200, 300]}
    ).to_csv(csv_file, index=False)
    return csv_file


def test_read_csv(sample_csv):
    df = DataReader(sample_csv).read_csv()
    assert len(df) == 3
    assert "id" in df.columns


def test_read_dispatches_on_extension(sample_csv):
    df = DataReader(sample_csv).read()
    assert list(df["name"]) == ["Alice", "Bob", "Charlie"]


def test_read_excel_roundtrip(tmp_path):
    xlsx = tmp_path / "sample.xlsx"
    pd.DataFrame({"a": [1, 2]}).to_excel(xlsx, index=False)
    df = DataReader(xlsx).read()
    assert list(df["a"]) == [1, 2]


def test_unsupported_extension(tmp_path):
    bad = tmp_path / "data.txt"
    bad.write_text("nope")
    with pytest.raises(ValueError):
        DataReader(bad).read()
