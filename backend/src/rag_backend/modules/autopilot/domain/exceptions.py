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
