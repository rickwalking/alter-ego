"""Per-model circuit breaker and failure classification (AE-0399).

A model's breaker is CLOSED (calls pass), OPEN (the model is skipped until
its cooldown ends) or HALF_OPEN (exactly one probe call may pass; everyone
else keeps skipping). The class of a failure decides what happens:

* ``FATAL`` (401/403, OpenCode ``FreeTierError``) and ``QUOTA`` (429 usage
  limit) open the breaker at once with a long cooldown;
* ``TRANSIENT`` (5xx, timeout, crash) opens it after N consecutive failures,
  and the cooldown doubles each time a probe fails (capped);
* ``THROTTLED`` (429 rate limit) and ``CONTENT`` (empty answer) never open it
  by themselves: the queue debounces or re-rolls them.

Every state change is published to the registry's listeners (logs, alerts).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from rag_backend.infrastructure.config.llm_queue_constants import (
    DEFAULT_BREAKER_COOLDOWN_SECONDS,
    DEFAULT_BREAKER_FAILURES,
    DEFAULT_BREAKER_FATAL_COOLDOWN_SECONDS,
    DEFAULT_BREAKER_MAX_COOLDOWN_SECONDS,
    DEFAULT_BREAKER_QUOTA_COOLDOWN_SECONDS,
    HEADER_RETRY_AFTER,
    MARKER_FREE_TIER,
    MARKERS_USAGE_LIMIT,
    STATUS_FORBIDDEN,
    STATUS_TOO_MANY_REQUESTS,
    STATUS_UNAUTHORIZED,
)


class FailureClass(StrEnum):
    """What a failed model call means for its breaker."""

    FATAL = "fatal"
    QUOTA = "quota"
    THROTTLED = "throttled"
    TRANSIENT = "transient"
    CONTENT = "content"


class BreakerState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class EmptyModelAnswerError(RuntimeError):
    """The model answered with no content and no tool call."""


@dataclass(frozen=True)
class BreakerPolicy:
    """Thresholds and cooldowns (seconds) of every breaker."""

    failure_threshold: int = DEFAULT_BREAKER_FAILURES
    cooldown: float = DEFAULT_BREAKER_COOLDOWN_SECONDS
    max_cooldown: float = DEFAULT_BREAKER_MAX_COOLDOWN_SECONDS
    quota_cooldown: float = DEFAULT_BREAKER_QUOTA_COOLDOWN_SECONDS
    fatal_cooldown: float = DEFAULT_BREAKER_FATAL_COOLDOWN_SECONDS


@dataclass(frozen=True)
class BreakerTransition:
    """One state change, published to the registry's listeners."""

    model: str
    old: BreakerState
    new: BreakerState
    failure: FailureClass | None = None
    cooldown: float | None = None
    reason: str = ""


Clock = Callable[[], float]
Listener = Callable[[BreakerTransition], None]
_FAILURE_OPENS_AT_ONCE: dict[FailureClass, str] = {
    FailureClass.FATAL: "fatal_cooldown",
    FailureClass.QUOTA: "quota_cooldown",
}


@dataclass
class ModelBreaker:
    """The breaker of one model."""

    model: str
    policy: BreakerPolicy
    clock: Clock
    publish: Listener
    state: BreakerState = BreakerState.CLOSED
    failures: int = 0
    open_until: float = 0.0
    cooldown: float = 0.0
    probe_in_flight: bool = False

    def try_acquire(self) -> bool:
        """True when a call may go to this model now."""
        if self.state is BreakerState.CLOSED:
            return True
        if self.state is BreakerState.OPEN and self.clock() >= self.open_until:
            self._move(BreakerState.HALF_OPEN)
        if self.state is BreakerState.HALF_OPEN and not self.probe_in_flight:
            self.probe_in_flight = True
            return True
        return False

    def record_success(self) -> None:
        """The model answered: close the breaker and reset the counters."""
        self.failures = 0
        self.cooldown = 0.0
        self.probe_in_flight = False
        if self.state is not BreakerState.CLOSED:
            self._move(BreakerState.CLOSED)

    def record_failure(self, failure: FailureClass, reason: str = "") -> None:
        """Count a failure; open the breaker when its class says so."""
        self.probe_in_flight = False
        long_cooldown = _FAILURE_OPENS_AT_ONCE.get(failure)
        if long_cooldown is not None:
            self._open(failure, getattr(self.policy, long_cooldown), reason)
            return
        if failure is not FailureClass.TRANSIENT:
            return
        self.failures += 1
        probing = self.state is BreakerState.HALF_OPEN
        if probing or self.failures >= self.policy.failure_threshold:
            self._open(failure, self._next_cooldown(), reason)

    def release_probe(self) -> None:
        """Let another caller probe (the probe ended without a verdict)."""
        self.probe_in_flight = False

    def describe(self) -> str:
        """``open(quota, 3540s left)`` style summary for errors and alerts."""
        if self.state is not BreakerState.OPEN:
            return self.state.value
        left = max(0, round(self.open_until - self.clock()))
        return f"{self.state.value}({left}s left)"

    def _next_cooldown(self) -> float:
        doubled = self.cooldown * 2 if self.cooldown else self.policy.cooldown
        return float(min(doubled, self.policy.max_cooldown))

    def _open(self, failure: FailureClass, cooldown: float, reason: str) -> None:
        self.cooldown = cooldown
        self.open_until = self.clock() + cooldown
        self._move(BreakerState.OPEN, failure=failure, reason=reason)

    def _move(
        self,
        new: BreakerState,
        *,
        failure: FailureClass | None = None,
        reason: str = "",
    ) -> None:
        old, self.state = self.state, new
        cooldown = self.cooldown if new is BreakerState.OPEN else None
        self.publish(BreakerTransition(self.model, old, new, failure, cooldown, reason))


@dataclass
class BreakerRegistry:
    """One breaker per model id, shared by every queue in the process."""

    policy: BreakerPolicy = field(default_factory=BreakerPolicy)
    clock: Clock = time.monotonic
    listeners: list[Listener] = field(default_factory=list)
    _breakers: dict[str, ModelBreaker] = field(default_factory=dict)

    def get(self, model: str) -> ModelBreaker:
        """The breaker of ``model`` (created closed on first use)."""
        if model not in self._breakers:
            self._breakers[model] = ModelBreaker(
                model, self.policy, self.clock, self._publish
            )
        return self._breakers[model]

    def subscribe(self, listener: Listener) -> None:
        """Receive every future state change."""
        if listener not in self.listeners:
            self.listeners.append(listener)

    def _publish(self, transition: BreakerTransition) -> None:
        for listener in list(self.listeners):
            listener(transition)


def classify_failure(exc: BaseException) -> FailureClass:
    """The failure class of a model error (see the module docstring)."""
    if isinstance(exc, EmptyModelAnswerError):
        return FailureClass.CONTENT
    if isinstance(exc, TimeoutError):
        return FailureClass.TRANSIENT
    return _class_of_status(getattr(exc, "status_code", None), str(exc))


def _class_of_status(status: object, text: str) -> FailureClass:
    if status in {STATUS_UNAUTHORIZED, STATUS_FORBIDDEN} or MARKER_FREE_TIER in text:
        return FailureClass.FATAL
    if status != STATUS_TOO_MANY_REQUESTS:
        return FailureClass.TRANSIENT
    if any(marker in text for marker in MARKERS_USAGE_LIMIT):
        return FailureClass.QUOTA
    return FailureClass.THROTTLED


def retry_after_seconds(exc: BaseException) -> float | None:
    """The server's ``Retry-After`` (seconds), when it sent one."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    raw = headers.get(HEADER_RETRY_AFTER) if headers is not None else None
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


__all__ = [
    "BreakerPolicy",
    "BreakerRegistry",
    "BreakerState",
    "BreakerTransition",
    "EmptyModelAnswerError",
    "FailureClass",
    "ModelBreaker",
    "classify_failure",
    "retry_after_seconds",
]
