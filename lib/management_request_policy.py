"""Transport-independent guards for a future loopback HTTP adapter.

No listener is created here. Callers must also bind only to 127.0.0.1, enforce
handler concurrency/deadlines, and avoid adding CORS response headers.
"""
from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from collections.abc import Callable
from urllib.parse import urlsplit


MAX_JSON_BODY_BYTES = 64 * 1024
ALLOWED_METHODS = frozenset({"GET", "POST"})


@dataclass(frozen=True)
class RequestDecision:
    allowed: bool
    reason: str


def _validate_expected_origin(origin: str) -> str:
    if not isinstance(origin, str):
        raise ValueError("origin must be a string")
    parsed = urlsplit(origin)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or parsed.port is None or not 1 <= parsed.port <= 65535):
        raise ValueError("expected origin must be an explicit HTTP loopback origin")
    return f"127.0.0.1:{parsed.port}"


class LoopbackRequestPolicy:
    """Exact local origin checks, bounded JSON, and a small global token bucket."""

    def __init__(
        self,
        expected_origin: str,
        *,
        max_body_bytes: int = MAX_JSON_BODY_BYTES,
        rate_per_second: float = 10.0,
        burst: int = 30,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.expected_host = _validate_expected_origin(expected_origin)
        parsed = urlsplit(expected_origin)
        self.expected_origin = f"{parsed.scheme}://{self.expected_host}"
        if type(max_body_bytes) is not int or not 1 <= max_body_bytes <= 1024 * 1024:
            raise ValueError("max JSON body must be from 1 byte to 1 MiB")
        if not isinstance(rate_per_second, (int, float)) or not 0 < rate_per_second <= 100:
            raise ValueError("request rate must be greater than zero and at most 100 per second")
        if type(burst) is not int or not 1 <= burst <= 300:
            raise ValueError("request burst must be from 1 to 300")
        self.max_body_bytes = max_body_bytes
        self.rate_per_second = float(rate_per_second)
        self.burst = burst
        self._clock = clock
        self._tokens = float(burst)
        self._updated_at = clock()
        self._lock = threading.Lock()

    def check(
        self,
        *,
        host: object,
        method: object,
        origin: object = None,
        content_type: object = None,
        content_length: object = 0,
    ) -> RequestDecision:
        """Validate one incoming request before body parsing or dispatch."""
        if not isinstance(host, str) or host != self.expected_host:
            return RequestDecision(False, "host_rejected")
        if not isinstance(method, str) or method not in ALLOWED_METHODS:
            return RequestDecision(False, "method_rejected")
        if origin is not None and origin != self.expected_origin:
            return RequestDecision(False, "origin_rejected")
        if method == "POST" and origin != self.expected_origin:
            return RequestDecision(False, "origin_required")
        if type(content_length) is not int or not 0 <= content_length <= self.max_body_bytes:
            return RequestDecision(False, "body_size_rejected")
        if method == "POST":
            if not isinstance(content_type, str):
                return RequestDecision(False, "content_type_rejected")
            normalized = content_type.strip().lower()
            if normalized not in {"application/json", "application/json; charset=utf-8"}:
                return RequestDecision(False, "content_type_rejected")
        if not self._consume_rate_token():
            return RequestDecision(False, "rate_limited")
        return RequestDecision(True, "accepted")

    def _consume_rate_token(self) -> bool:
        with self._lock:
            now = self._clock()
            elapsed = max(0.0, now - self._updated_at)
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate_per_second)
            self._updated_at = now
            if self._tokens < 1.0:
                return False
            self._tokens -= 1.0
            return True
