import pytest
import yaml

from config.etl_config import ETLConfig


def _write(tmp_path, data):
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return str(p)


def _valid(**overrides):
    base = {
        "name": "p",
        "source": {"type": "csv", "path": "x.csv"},
        "target": {"table": "t"},
    }
    base.update(overrides)
    return base


def test_loads_and_maps_validate_alias(tmp_path):
    path = _write(tmp_path, _valid(validate={"no_nulls": ["id"]}))
    cfg = ETLConfig.from_yaml(path)
    assert cfg.name == "p"
    assert cfg.validation.no_nulls == ["id"]      # 'validate' -> validation
    assert cfg.target.if_exists == "append"       # default applied


def test_incremental_requires_watermark(tmp_path):
    path = _write(tmp_path, _valid(incremental=True))
    with pytest.raises(ValueError):
        ETLConfig.from_yaml(path)


def test_incremental_with_watermark_ok(tmp_path):
    path = _write(tmp_path, _valid(incremental=True, watermark_column="id"))
    cfg = ETLConfig.from_yaml(path)
    assert cfg.incremental and cfg.watermark_column == "id"
