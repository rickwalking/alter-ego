"""AE-0446: pytest runs with ``filterwarnings = error`` (``pytest.ini``).

Seeded-violation test for the gate (AE-0180): a warning emitted inside a test
must raise, not just print a summary line. If the ``error`` filter is dropped
from ``pytest.ini``, ``warnings.warn`` returns normally and this test fails.
"""

import warnings

import pytest

_SEEDED_MESSAGE = "ae-0446 seeded warning"


# Scenario: a project warning fails the test run instead of being printed.
def test_a_warning_inside_a_test_is_an_error() -> None:
    with pytest.raises(DeprecationWarning, match=_SEEDED_MESSAGE):
        warnings.warn(_SEEDED_MESSAGE, DeprecationWarning, stacklevel=1)
