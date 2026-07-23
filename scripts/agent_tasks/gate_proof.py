"""Machine-readable gate-proof + declared-QA-mode checks (AE-0258, AE-0260).

These checks gate the move-time transitions only (``can_transition`` invoked by
``move_ticket.py`` with ``enforce_gate_proof=True``). They are deliberately NOT
wired into the retroactive ``validate_ticket_file`` sweep so the 164 tickets that
reached Dev Complete / Review before the proof existed stay green (grandfathered);
new transitions must carry the proof.

The proof is a self-pasted ``GATES_JSON:`` line — forgeable by design. Its real
authority is CI re-running every gate on the same commit, where a forged PASS
surfaces as red. This module is an observability + friction ratchet, not a
forgery-proof control (AE-0258 Non-Goals).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.agent_tasks.constants import (
    ALLOWED_QA_MODES,
    DIRTY_WAIVER_RE,
    GATES_COMMIT_FIELD_RE,
    GATES_DIRTY_FIELD_RE,
    GATES_FAIL_FIELD_RE,
    GATES_JSON_MARKER,
    GATES_SKIP_FIELD_RE,
    QA_MODE_FIELD_RE,
    WAVE_REPORT_PREFIX,
)


@dataclass(frozen=True)
class ProofOutcome:
    """Result of evaluating a report's gate proof: hard errors + soft warnings."""

    errors: list[str]
    warnings: list[str]


def _resolve_proof_text(report: Path) -> str | None:
    """Return the text carrying the GATES_JSON line, following a wave reference.

    A per-ticket report MAY satisfy the proof by referencing a sibling wave
    report (``wave-*.qa.md`` / ``wave-*.md``) that carries the GATES_JSON line
    (AE-0258 wave-reports AC). The reference is any ``wave-...`` token in the body
    that names an existing sibling file.
    """
    try:
        text = report.read_text(encoding="utf-8")
    except OSError:
        return None
    if GATES_JSON_MARKER in text:
        return text
    referenced = _referenced_wave_report(report, text)
    if referenced is None:
        return None
    try:
        return referenced.read_text(encoding="utf-8")
    except OSError:
        return None


def _referenced_wave_report(report: Path, text: str) -> Path | None:
    """Find a sibling ``wave-*`` report named in ``text`` that exists on disk."""
    for sibling in sorted(report.parent.glob(f"{WAVE_REPORT_PREFIX}*")):
        if sibling.name in text and GATES_JSON_MARKER in _safe_read(sibling):
            return sibling
    return None


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _gates_line(text: str) -> str | None:
    """Return the first line containing the GATES_JSON marker, else None."""
    for line in text.splitlines():
        if GATES_JSON_MARKER in line:
            return line
    return None


def _verdict_errors(gates_line: str, label: str) -> list[str]:
    """Block on fail>0 (AE-0258). Lenient field-regex on the raw line."""
    fail_match = GATES_FAIL_FIELD_RE.search(gates_line)
    if fail_match is None:
        return [f'{label} GATES_JSON proof has no parseable "fail" field.']
    if int(fail_match.group(1)) > 0:
        return [
            f"{label} GATES_JSON reports fail>0 "
            f"({fail_match.group(1)} failing gate(s)) — fix the gates, do not advance."
        ]
    return []


def _dirty_errors(gates_line: str, waiver_text: str, label: str) -> list[str]:
    """Block on dirty>0 without a DIRTY_WAIVER: line (AE-0322).

    gate-capture.sh stamps ``"dirty":N`` when it ran with
    GATE_CAPTURE_ALLOW_DIRTY=1 over N uncommitted in-scope source files —
    diff-based gates did NOT see that work, so the proof is tainted unless the
    dev-summary waives it (naming the files and why they belong to other
    sessions). An absent dirty field (pre-AE-0322 wrappers) is not an error.
    """
    match = GATES_DIRTY_FIELD_RE.search(gates_line)
    if match is None or int(match.group(1)) == 0:
        return []
    if DIRTY_WAIVER_RE.search(waiver_text):
        return []
    return [
        f"{label} GATES_JSON reports dirty>0 ({match.group(1)} uncommitted "
        f"in-scope source file(s)) — diff-based gates cannot see uncommitted "
        f"work (AE-0322). Commit and re-run gates, or add a line "
        f"`DIRTY_WAIVER: <files — why they belong to other sessions>` "
        f"to the report."
    ]


def _dirty_warnings(gates_line: str, waiver_text: str, label: str) -> list[str]:
    """A waived dirty run stays visible as a warning (AE-0322)."""
    match = GATES_DIRTY_FIELD_RE.search(gates_line)
    if match is None or int(match.group(1)) == 0:
        return []
    if not DIRTY_WAIVER_RE.search(waiver_text):
        return []
    return [
        f"{label} gate run was over a dirty tree ({match.group(1)} in-scope "
        f"file(s)), waived by DIRTY_WAIVER — CI on the committed tree is the "
        f"final authority (AE-0322)."
    ]


def _skip_warnings(gates_line: str, label: str) -> list[str]:
    """skip>0 ⇒ WARNING, not a block — CI (GATES_REQUIRE_ALL=1) decides skips."""
    skip_match = GATES_SKIP_FIELD_RE.search(gates_line)
    if skip_match is None or int(skip_match.group(1)) == 0:
        return []
    return [
        f"{label} GATES_JSON reports skip>0 ({skip_match.group(1)} skipped) — "
        f"CI (GATES_REQUIRE_ALL=1) is the authority on skipped gates."
    ]


def _commit_warnings(proof_text: str, head_sha: str | None, label: str) -> list[str]:
    """SHA mismatch between the report's pinned commit and branch HEAD ⇒ WARNING."""
    if head_sha is None:
        return []
    match = GATES_COMMIT_FIELD_RE.search(proof_text)
    if match is None:
        return []
    pinned = match.group(1).lower()
    if not head_sha.lower().startswith(pinned) and not pinned.startswith(
        head_sha.lower()
    ):
        return [
            f"{label} GATES_JSON is pinned to commit {pinned} but branch HEAD is "
            f"{head_sha[:12]} — re-run gates on HEAD or confirm the report is current."
        ]
    return []


def evaluate_gate_proof(
    report: Path, label: str, head_sha: str | None = None
) -> ProofOutcome:
    """Evaluate the GATES_JSON proof in ``report`` (AE-0258).

    Missing proof or fail>0 ⇒ error (blocks). skip>0 or SHA mismatch ⇒ warning.
    A per-ticket report may reference a wave report carrying the proof.
    """
    proof_text = _resolve_proof_text(report)
    if proof_text is None:
        return ProofOutcome(
            errors=[
                f"{label} is missing the machine-readable GATES_JSON proof "
                f"(AE-0258). Paste the `GATES_JSON:` line from gates.sh "
                f"(or reference a wave-*.qa.md that carries it)."
            ],
            warnings=[],
        )
    gates_line = _gates_line(proof_text)
    if gates_line is None:  # defensive: _resolve_proof_text guaranteed the marker
        return ProofOutcome(
            errors=[f"{label} GATES_JSON marker present but no line found."],
            warnings=[],
        )
    # The waiver may live in the per-ticket report even when the GATES_JSON
    # proof is inherited from a wave report — search both texts (AE-0322).
    waiver_text = proof_text + "\n" + _safe_read(report)
    errors = _verdict_errors(gates_line, label) + _dirty_errors(
        gates_line, waiver_text, label
    )
    warnings = (
        _skip_warnings(gates_line, label)
        + _dirty_warnings(gates_line, waiver_text, label)
        + _commit_warnings(proof_text, head_sha, label)
    )
    return ProofOutcome(errors=errors, warnings=warnings)


def evaluate_qa_mode(report: Path, label: str) -> list[str]:
    """Block a Review whose .qa.md omits ``mode:`` or uses a non-allowed value.

    External QA is the default/required mode for agent/same-session work; the
    validator can only check the declared field — it CANNOT detect "same session"
    (AE-0260 Non-Goals). A per-ticket report may inherit the field from a
    referenced wave report (one external run over N tickets).
    """
    text = _resolve_mode_text(report)
    if text is None:
        return [f"{label} could not be read for the declared QA mode (AE-0260)."]
    match = QA_MODE_FIELD_RE.search(text)
    if match is None:
        return [
            f"{label} is missing the declared `mode:` field (AE-0260). Declare one "
            f"of: {', '.join(ALLOWED_QA_MODES)} (external is the default)."
        ]
    value = match.group(1).lower()
    if value not in ALLOWED_QA_MODES:
        return [
            f"{label} declares an invalid QA mode '{value}' (AE-0260). "
            f"Allowed: {', '.join(ALLOWED_QA_MODES)}."
        ]
    return []


def _resolve_mode_text(report: Path) -> str | None:
    """Read the report; if it has no ``mode:`` field, follow a wave reference."""
    try:
        text = report.read_text(encoding="utf-8")
    except OSError:
        return None
    if QA_MODE_FIELD_RE.search(text):
        return text
    referenced = _referenced_wave_report(report, text)
    if referenced is None:
        return text
    wave_text = _safe_read(referenced)
    return wave_text if QA_MODE_FIELD_RE.search(wave_text) else text
