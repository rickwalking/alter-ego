"""Domain errors for the autopilot bounded context."""

from __future__ import annotations

from rag_backend.modules.autopilot.constants import INVALID_TRANSITION_MESSAGE
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionPair,
)


class InvalidAutopilotTransitionError(Exception):
    """The requested state pair is not in the architecture §4 table.

    Raised as ``InvalidAutopilotTransition`` (AE-0350). The class carries the
    ``Error`` suffix the linter requires; the alias is the name the ticket
    and the feature file use.
    """

    def __init__(self, pair: TransitionPair) -> None:
        self.pair = pair
        super().__init__(
            f"{INVALID_TRANSITION_MESSAGE}: {pair.expected.value} -> {pair.new.value}"
        )

    @property
    def expected(self) -> AutopilotRunState:
        """State the caller claimed the run was in."""
        return self.pair.expected

    @property
    def new(self) -> AutopilotRunState:
        """State the caller wanted to move to."""
        return self.pair.new


# Ticket and Gherkin name for InvalidAutopilotTransitionError.
InvalidAutopilotTransition = InvalidAutopilotTransitionError


class InstagramCallError(Exception):
    """A Graph failure translated for the publish job.

    ``transient`` is True for 5xx, rate limits, and container poll timeouts.
    Permanent failures (4xx auth/format, including Meta code 36003) are False.
    """

    def __init__(self, *, status_code: int, error_code: str, transient: bool) -> None:
        super().__init__(error_code)
        self.status_code = status_code
        self.error_code = error_code
        self.transient = transient
