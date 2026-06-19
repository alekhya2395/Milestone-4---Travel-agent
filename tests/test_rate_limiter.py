import pytest

from travel_agent.llm.rate_limiter import (
    RateLimitExceededError,
    RateLimiter,
    estimate_calls_per_run,
    reset_limiters_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_limiters():
    reset_limiters_for_tests()
    yield
    reset_limiters_for_tests()


def test_acquire_within_rpm_limit():
    limiter = RateLimiter(provider="test", rpm=10, rpd=100)
    for _ in range(5):
        limiter.acquire()
    status = limiter.status()
    assert status.rpm_used == 5


def test_rpd_raises_when_exhausted():
    limiter = RateLimiter(provider="test", rpm=100, rpd=2)
    limiter.acquire()
    limiter.acquire()
    with pytest.raises(RateLimitExceededError, match="daily limit"):
        limiter.acquire()


def test_status_reports_usage():
    limiter = RateLimiter(provider="test", rpm=10, rpd=50)
    limiter.acquire()
    status = limiter.status()
    assert status.rpm_used == 1
    assert status.rpd_used == 1
    assert status.rpm_remaining == 9
    assert status.rpd_remaining == 49


def test_estimate_calls_per_run_defaults():
    est = estimate_calls_per_run(validation_retries=1, json_repair_retries=1)
    assert est["groq_min"] == 6
    assert est["groq_max"] == 12
    assert est["gemini_min"] == 4
    assert est["gemini_max"] == 8


def test_estimate_calls_happy_path():
    est = estimate_calls_per_run(validation_retries=0, json_repair_retries=0)
    assert est == {"groq_min": 5, "groq_max": 5, "gemini_min": 2, "gemini_max": 2}
