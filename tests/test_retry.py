import pytest

from utils.retry import with_retry

_NO_SLEEP = lambda _: None  # noqa: E731  -- keep tests instant


def test_succeeds_after_transient_failures():
    calls = {"n": 0}

    @with_retry(max_attempts=3, base_delay=0, sleep=_NO_SLEEP)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_raises_after_exhausting_attempts():
    calls = {"n": 0}

    @with_retry(max_attempts=2, base_delay=0, sleep=_NO_SLEEP)
    def always_fails():
        calls["n"] += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        always_fails()
    assert calls["n"] == 2


def test_only_retries_listed_exceptions():
    @with_retry(max_attempts=3, base_delay=0, exceptions=(ValueError,), sleep=_NO_SLEEP)
    def raises_key_error():
        raise KeyError("not retried")

    with pytest.raises(KeyError):
        raises_key_error()
