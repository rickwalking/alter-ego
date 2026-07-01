"""Extended unit tests for carousel workflow phases.

Feature: 7-phase carousel editorial workflow with human gates
"""

from typing import NamedTuple
from unittest.mock import patch

import pytest

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.agents.carousel_workflow_graph import (
    build_carousel_workflow_graph,
    route_after_final_review,
    route_after_gate,
    route_after_hold,
)
from rag_backend.agents.carousel_workflow_nodes import (
    await_human_review,
    brief_phase,
    content_phase,
    design_phase,
    final_review_phase,
    images_phase,
    outline_phase,
    research_phase,
    review_updates_from_response,
)
from rag_backend.application.services.carousel.workflow_state import (
    get_initial_carousel_state,
)
from rag_backend.domain.constants.carousel_workflow import (
    INTERRUPT_TYPE_CONTENT_REVIEW,
    INTERRUPT_TYPE_DESIGN_REVIEW,
    INTERRUPT_TYPE_OUTLINE_REVIEW,
    INTERRUPT_TYPE_RESEARCH_REVIEW,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
    SEND_BACK_TARGET_PHASE_KEY,
    STRUCTURED_FEEDBACK_KEY,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)


def _state(**overrides: object) -> dict[str, object]:
    state = get_initial_carousel_state("project-1", {"topic": "AI"})
    state.update(overrides)
    return state


@pytest.mark.unit
class TestAwaitHumanReview:
    """Tests for the shared human-review interrupt helper."""

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_approve_returns_approved_status(self, mock_interrupt: object) -> None:
        """Given approve action, when awaiting review, then phase is approved."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        result = await_human_review(
            _state(),
            PHASE_RESEARCH,
            INTERRUPT_TYPE_RESEARCH_REVIEW,
            {"message": "Review research findings."},
        )

        assert result["phase_status"] == PHASE_STATUS_APPROVED

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_reject_returns_awaiting_human(self, mock_interrupt: object) -> None:
        """Given reject action, when awaiting review, then workflow waits for human."""
        mock_interrupt.return_value = {"action": "reject"}

        result = await_human_review(
            _state(),
            PHASE_OUTLINE,
            INTERRUPT_TYPE_OUTLINE_REVIEW,
            {"message": "Review outline."},
        )

        assert result["phase_status"] == PHASE_STATUS_AWAITING_HUMAN

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_revise_returns_awaiting_human(self, mock_interrupt: object) -> None:
        """Given revise action, when awaiting review, then workflow waits for human."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_REVISE}

        result = await_human_review(
            _state(),
            PHASE_RESEARCH,
            INTERRUPT_TYPE_RESEARCH_REVIEW,
            {"message": "Review research findings."},
        )

        assert result["phase_status"] == PHASE_STATUS_AWAITING_HUMAN

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_non_dict_response_awaits_human(self, mock_interrupt: object) -> None:
        """Given invalid interrupt payload, when awaiting review, then human is awaited."""
        mock_interrupt.return_value = "invalid"

        result = await_human_review(
            _state(),
            PHASE_CONTENT,
            INTERRUPT_TYPE_CONTENT_REVIEW,
            {"message": "Review content."},
        )

        assert result["phase_status"] == PHASE_STATUS_AWAITING_HUMAN

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_interrupt_payload_includes_project_and_phase(
        self, mock_interrupt: object
    ) -> None:
        """Given state, when awaiting review, then interrupt payload is complete."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        await_human_review(
            _state(project_id="proj-42"),
            PHASE_DESIGN,
            INTERRUPT_TYPE_DESIGN_REVIEW,
            {"message": "Review design."},
        )

        payload = mock_interrupt.call_args[0][0]
        assert payload["type"] == INTERRUPT_TYPE_DESIGN_REVIEW
        assert payload["phase"] == PHASE_DESIGN
        assert payload["project_id"] == "proj-42"
        assert payload["message"] == "Review design."


@pytest.mark.unit
class TestBuildCarouselWorkflowGraph:
    """Tests for workflow graph construction."""

    def test_graph_includes_all_phase_nodes(self) -> None:
        """Given builder, when graph is created, then every phase node exists."""
        from rag_backend.domain.constants.carousel_workflow import PHASE_APPROVED_HOLD

        graph = build_carousel_workflow_graph()

        for phase in (
            PHASE_RESEARCH,
            PHASE_OUTLINE,
            PHASE_CONTENT,
            PHASE_DESIGN,
            PHASE_IMAGES,
            PHASE_FINAL_REVIEW,
            PHASE_APPROVED_HOLD,
        ):
            assert phase in graph.nodes


@pytest.mark.unit
class TestWorkflowPhaseNodes:
    """Direct tests for individual workflow phase nodes."""

    def test_brief_phase_moves_to_research(self) -> None:
        """Given brief phase, when executed, then research starts."""
        result = brief_phase(_state())

        assert result["current_phase"] == PHASE_RESEARCH
        assert result["phase_status"] == PHASE_STATUS_IN_PROGRESS
        assert result["brief_approved"] is True

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_research_phase_approves(self, mock_interrupt: object) -> None:
        """Given approved research review, when phase runs, then research is approved."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        result = research_phase(_state(research_findings=[{"title": "Finding"}]))

        assert result["research_approved"] is True
        assert result["current_phase"] == PHASE_RESEARCH
        assert result["phase_status"] == PHASE_STATUS_APPROVED

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_research_phase_passes_findings_to_interrupt(
        self, mock_interrupt: object
    ) -> None:
        """Given research findings, when phase runs, then findings are in interrupt payload."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}
        findings = [{"title": "Security trend", "source": "report"}]

        research_phase(_state(research_findings=findings))

        payload = mock_interrupt.call_args[0][0]
        assert payload["findings"] == findings

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_outline_phase_passes_outline_to_interrupt(
        self, mock_interrupt: object
    ) -> None:
        """Given outline slides, when phase runs, then outline is in interrupt payload."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}
        outline = [{"slide": 1, "title": "Intro"}]

        outline_phase(_state(outline=outline))

        payload = mock_interrupt.call_args[0][0]
        assert payload["outline"] == outline

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_outline_phase_rejects(self, mock_interrupt: object) -> None:
        """Given rejected outline review, when phase runs, then outline stays unapproved."""
        mock_interrupt.return_value = {"action": "reject"}

        result = outline_phase(_state(outline=[{"slide": 1}]))

        assert result["outline_approved"] is False
        assert result["current_phase"] == PHASE_OUTLINE

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_content_phase_approves(self, mock_interrupt: object) -> None:
        """Given approved content review, when phase runs, then content is approved."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        result = content_phase(_state(slide_drafts=[{"slide": 1, "body": "Draft"}]))

        assert result["content_approved"] is True
        assert result["current_phase"] == PHASE_CONTENT

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_content_phase_passes_drafts_to_interrupt(
        self, mock_interrupt: object
    ) -> None:
        """Given slide drafts, when phase runs, then drafts are in interrupt payload."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}
        drafts = [{"slide": 2, "body": "Draft copy"}]

        content_phase(_state(slide_drafts=drafts))

        payload = mock_interrupt.call_args[0][0]
        assert payload["slide_drafts"] == drafts

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_design_phase_marks_design_applied(self, mock_interrupt: object) -> None:
        """Given approved design review, when phase runs, then design is applied."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        result = design_phase(_state(design_applied=False))

        assert result["design_applied"] is True
        assert result["design_approved"] is True
        assert result["current_phase"] == PHASE_DESIGN

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_design_phase_passes_design_flag_to_interrupt(
        self, mock_interrupt: object
    ) -> None:
        """Given design state, when phase runs, then design flag is in interrupt payload."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        design_phase(_state(design_applied=True))

        payload = mock_interrupt.call_args[0][0]
        assert payload["design_applied"] is True

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_images_phase_approves_assets(self, mock_interrupt: object) -> None:
        """Given approved image review, when phase runs, then images are approved."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        result = images_phase(_state(image_assets=["slide_1.jpg"]))

        assert result["images_approved"] is True
        assert result["current_phase"] == PHASE_IMAGES

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_images_phase_passes_assets_to_interrupt(
        self, mock_interrupt: object
    ) -> None:
        """Given image assets, when phase runs, then assets are in interrupt payload."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}
        assets = ["slide_1.jpg", "slide_2.jpg"]

        images_phase(_state(image_assets=assets))

        payload = mock_interrupt.call_args[0][0]
        assert payload["image_assets"] == assets

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_final_review_phase_approves_for_publish_when_approved(
        self, mock_interrupt: object
    ) -> None:
        """Given approved final review, when phase runs, then workflow is approved for publish."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        result = final_review_phase(_state(rubric_scores={"tone": 90}))

        assert result["quality_passed"] is True
        assert result["current_phase"] == PHASE_FINAL_REVIEW
        assert result["workflow_status"] == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
        assert result["status"] == "draft"

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_final_review_phase_clears_send_back_target_on_approval(
        self, mock_interrupt: object
    ) -> None:
        """AE-0288: approval clears any stale send_back_target_phase so a later
        resume from the approved_hold node cannot route on it."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        result = final_review_phase(
            _state(
                rubric_scores={"tone": 90},
                **{SEND_BACK_TARGET_PHASE_KEY: PHASE_CONTENT},
            )
        )

        assert result["quality_passed"] is True
        assert result[SEND_BACK_TARGET_PHASE_KEY] == ""

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_final_review_phase_passes_rubric_scores_to_interrupt(
        self, mock_interrupt: object
    ) -> None:
        """Given rubric scores, when phase runs, then scores are in interrupt payload."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}
        scores = {"tone": 90.0, "clarity": 85.0}

        final_review_phase(_state(rubric_scores=scores))

        payload = mock_interrupt.call_args[0][0]
        assert payload["rubric_scores"] == scores

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_final_review_phase_stays_draft_when_rejected(
        self, mock_interrupt: object
    ) -> None:
        """Given rejected final review, when phase runs, then project stays draft."""
        mock_interrupt.return_value = {"action": "reject"}

        result = final_review_phase(_state())

        assert result["quality_passed"] is False
        assert result["current_phase"] == PHASE_FINAL_REVIEW
        assert result["status"] == "draft"

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_final_review_phase_preserves_content_phase_on_send_back(
        self, mock_interrupt: object
    ) -> None:
        """AE-0290: a send-back to content must record current_phase=content (not
        clobber it back to final_review), so read_checkpoint_phase reports content
        and the edited-localized-slides gate accepts the edits."""
        mock_interrupt.return_value = {
            "action": REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY: {
                STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_CONTENT,
            },
        }

        result = final_review_phase(_state())

        assert result["current_phase"] == PHASE_CONTENT
        # AE-0290: target must stay set so route_after_final_review can route.
        assert result[SEND_BACK_TARGET_PHASE_KEY] == PHASE_CONTENT
        assert result["quality_passed"] is False

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_final_review_phase_preserves_images_phase_on_send_back(
        self, mock_interrupt: object
    ) -> None:
        """AE-0290: send-back to a non-content phase is preserved too."""
        mock_interrupt.return_value = {
            "action": REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY: {
                STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_IMAGES,
            },
        }

        result = final_review_phase(_state())

        assert result["current_phase"] == PHASE_IMAGES
        assert result[SEND_BACK_TARGET_PHASE_KEY] == PHASE_IMAGES

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_final_review_phase_rejects_bogus_send_back_target(
        self, mock_interrupt: object
    ) -> None:
        """AE-0290 membership guard: a target outside CAROUSEL_WORKFLOW_PHASES never
        reaches current_phase — the node falls back to final_review."""
        mock_interrupt.return_value = {
            "action": REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY: {
                STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: "banana",
            },
        }

        result = final_review_phase(_state())

        assert result["current_phase"] == PHASE_FINAL_REVIEW
        assert SEND_BACK_TARGET_PHASE_KEY not in result


@pytest.mark.unit
class TestWorkflowRouting:
    """Tests for conditional routing helpers."""

    def testroute_after_gate_returns_approved(self) -> None:
        """Given approved field, when routing, then approved path is chosen."""
        assert (
            route_after_gate(_state(research_approved=True), "research_approved")
            == "approved"
        )

    def testroute_after_gate_returns_retry(self) -> None:
        """Given unapproved field, when routing, then retry path is chosen."""
        assert (
            route_after_gate(_state(research_approved=False), "research_approved")
            == "retry"
        )

    def testroute_after_final_review_send_back_to_content(self) -> None:
        """Given final review send-back, when routing, then target phase is chosen."""
        assert (
            route_after_final_review(
                _state(
                    quality_passed=False,
                    **{SEND_BACK_TARGET_PHASE_KEY: PHASE_CONTENT},
                )
            )
            == PHASE_CONTENT
        )

    def test_structured_feedback_sets_send_back_target(self) -> None:
        """Given structured feedback, when parsing review, then target phase is set."""
        updates = review_updates_from_response({
            "action": REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY: {
                STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_OUTLINE,
            },
        })

        assert updates[SEND_BACK_TARGET_PHASE_KEY] == PHASE_OUTLINE
        assert updates["current_phase"] == PHASE_OUTLINE
        # AE-0288: any revise drops the publish approval in graph state.
        assert updates["workflow_status"] == "draft"
        assert updates["quality_passed"] is False

    def test_revise_without_target_drops_publish_approval(self) -> None:
        """AE-0288: a revise WITHOUT a target still clears the publish approval,
        so a held carousel cannot keep approved_for_publish during a revise."""
        updates = review_updates_from_response({"action": REVIEW_ACTION_REVISE})

        assert updates["phase_status"] == "awaiting_human"
        assert updates["workflow_status"] == "draft"
        assert updates["quality_passed"] is False
        assert SEND_BACK_TARGET_PHASE_KEY not in updates

    def testroute_after_hold_send_back_to_target(self) -> None:
        """AE-0288: a send-back resume from the hold routes to the target phase."""
        assert (
            route_after_hold(
                _state(
                    phase_status="awaiting_human",
                    **{SEND_BACK_TARGET_PHASE_KEY: PHASE_CONTENT},
                )
            )
            == PHASE_CONTENT
        )

    def testroute_after_hold_approve_finalizes(self) -> None:
        """AE-0288: an approve resume from the hold finalizes (END)."""
        assert (
            route_after_hold(
                _state(
                    phase_status="approved",
                    **{SEND_BACK_TARGET_PHASE_KEY: PHASE_CONTENT},
                )
            )
            == "done"
        )

    def testroute_after_hold_ignores_stale_target_without_revise(self) -> None:
        """AE-0288: a non-awaiting_human resume must NOT route on a stale
        send_back_target_phase left from a prior cycle — it finalizes instead."""
        assert (
            route_after_hold(
                _state(
                    phase_status="approved",
                    **{SEND_BACK_TARGET_PHASE_KEY: PHASE_OUTLINE},
                )
            )
            == "done"
        )


@pytest.mark.unit
class TestCarouselWorkflowEngineLifecycle:
    """Tests for workflow engine resume and state loading."""

    @pytest.mark.asyncio
    async def test_resume_invokes_graph_with_human_input(self) -> None:
        """Given human input, when resuming, then graph is invoked with thread id."""
        engine = CarouselWorkflowEngine()
        engine._app = AsyncMockWrapper()

        result = await engine.resume(
            "project-9", {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"}
        )

        assert result["project_id"] == "project-9"
        assert engine._app.last_config == {"configurable": {"thread_id": "project-9"}}

    @pytest.mark.asyncio
    async def test_get_state_returns_none_when_snapshot_missing(self) -> None:
        """Given missing snapshot, when loading state, then None is returned."""
        engine = CarouselWorkflowEngine()
        engine._app = AsyncMockWrapper(snapshot=None)

        result = await engine.get_state("missing-project")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_state_returns_values_when_present(self) -> None:
        """Given persisted snapshot, when loading state, then values are returned."""
        engine = CarouselWorkflowEngine()
        expected = _state(project_id="project-77")
        engine._app = AsyncMockWrapper(snapshot=Snapshot(values=expected))

        result = await engine.get_state("project-77")

        assert result == expected

    async def test_get_state_returns_none_when_values_not_dict(self) -> None:
        """Given non-dict snapshot values, when loading state, then None is returned."""
        engine = CarouselWorkflowEngine()
        engine._app = AsyncMockWrapper(snapshot=Snapshot(values="invalid"))

        result = await engine.get_state("project-77")

        assert result is None


class Snapshot(NamedTuple):
    """Minimal LangGraph state snapshot stub."""

    values: dict[str, object] | None


class AsyncMockWrapper:
    """Minimal compiled graph stub for engine lifecycle tests."""

    def __init__(self, snapshot: Snapshot | None = None) -> None:
        self.snapshot = snapshot
        self.last_config: dict[str, object] | None = None

    async def ainvoke(
        self,
        payload: dict[str, object] | object | None,
        *,
        config: dict[str, object],
    ) -> dict[str, object]:
        self.last_config = config
        if isinstance(payload, dict):
            return payload
        return _state(project_id=str(config["configurable"]["thread_id"]))

    async def aget_state(self, config: dict[str, object]) -> Snapshot | None:
        return self.snapshot
