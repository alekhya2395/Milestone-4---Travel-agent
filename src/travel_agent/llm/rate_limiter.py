"""Thread-safe RPM and RPD rate limiting for LLM API calls."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


class RateLimitExceededError(RuntimeError):
    """Raised when the daily request quota is exhausted."""


@dataclass
class RateLimitStatus:
    provider: str
    rpm_limit: int
    rpm_used: int
    rpd_limit: int | None
    rpd_used: int
    tpm_limit: int | None = None

    @property
    def rpm_remaining(self) -> int:
        return max(0, self.rpm_limit - self.rpm_used)

    @property
    def rpd_remaining(self) -> int | None:
        if self.rpd_limit is None:
            return None
        return max(0, self.rpd_limit - self.rpd_used)


class RateLimiter:
    """Sliding-window RPM limiter with a rolling 24-hour RPD counter."""

    def __init__(
        self,
        *,
        provider: str,
        rpm: int,
        rpd: int | None = None,
        tpm: int | None = None,
    ) -> None:
        self.provider = provider
        self.rpm = rpm
        self.rpd = rpd
        self.tpm = tpm  # documented ceiling; not enforced without token counting
        self._lock = threading.Lock()
        self._minute_window: deque[float] = deque()
        self._day_window: deque[float] = deque()

    def _prune(self, now: float) -> None:
        minute_ago = now - 60.0
        day_ago = now - 86400.0
        while self._minute_window and self._minute_window[0] <= minute_ago:
            self._minute_window.popleft()
        while self._day_window and self._day_window[0] <= day_ago:
            self._day_window.popleft()

    def _wait_for_rpm(self, now: float) -> None:
        while len(self._minute_window) >= self.rpm:
            sleep_for = 60.0 - (now - self._minute_window[0]) + 0.05
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.time()
            self._prune(now)

    def acquire(self) -> None:
        with self._lock:
            now = time.time()
            self._prune(now)

            if self.rpd is not None and len(self._day_window) >= self.rpd:
                raise RateLimitExceededError(
                    f"{self.provider} daily limit reached ({self.rpd} RPD). "
                    "Try again tomorrow or raise limits in config."
                )

            self._wait_for_rpm(now)
            now = time.time()
            self._prune(now)

            self._minute_window.append(now)
            self._day_window.append(now)

    def status(self) -> RateLimitStatus:
        with self._lock:
            now = time.time()
            self._prune(now)
            return RateLimitStatus(
                provider=self.provider,
                rpm_limit=self.rpm,
                rpm_used=len(self._minute_window),
                rpd_limit=self.rpd,
                rpd_used=len(self._day_window),
                tpm_limit=self.tpm,
            )


# Process-wide singletons — shared across all client instances in one run.
_groq_limiter: RateLimiter | None = None
_gemini_limiter: RateLimiter | None = None
_limiter_lock = threading.Lock()


def get_groq_limiter(*, rpm: int, rpd: int | None, tpm: int | None) -> RateLimiter:
    global _groq_limiter
    with _limiter_lock:
        if _groq_limiter is None:
            _groq_limiter = RateLimiter(
                provider="groq",
                rpm=rpm,
                rpd=rpd,
                tpm=tpm,
            )
        return _groq_limiter


def get_gemini_limiter(*, rpm: int, rpd: int | None, tpm: int | None) -> RateLimiter:
    global _gemini_limiter
    with _limiter_lock:
        if _gemini_limiter is None:
            _gemini_limiter = RateLimiter(
                provider="gemini",
                rpm=rpm,
                rpd=rpd,
                tpm=tpm,
            )
        return _gemini_limiter


def reset_limiters_for_tests() -> None:
    global _groq_limiter, _gemini_limiter
    with _limiter_lock:
        _groq_limiter = None
        _gemini_limiter = None


def estimate_calls_per_run(*, validation_retries: int = 0, json_repair_retries: int = 0) -> dict[str, int]:
    """
    Estimate API calls for one pipeline run.

    groq_min / gemini_min = happy path (no JSON repair loops).
    groq_max / gemini_max = worst case if every call needs max JSON repairs.
    """
    groq_base = 5  # parser + 3 gather + composer
    gemini_base = 2  # budget + validator
    groq_retries = validation_retries  # composer re-run
    gemini_retries = validation_retries * 2  # budget + validator per retry

    groq_happy = groq_base + groq_retries
    gemini_happy = gemini_base + gemini_retries
    repair_multiplier = 1 + json_repair_retries

    return {
        "groq_min": groq_happy,
        "groq_max": groq_happy * repair_multiplier,
        "gemini_min": gemini_happy,
        "gemini_max": gemini_happy * repair_multiplier,
    }
