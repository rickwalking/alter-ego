"""Unit test for image-phase revision feedback persistence (AE-0261).

Gherkin: tests/features/image_generation_provider.feature
(Scenario: image revision feedback updates the prompt).

A revise on the image phase appends the feedback to the project's
``custom_visual_details`` *before* the graph re-runs, so the reloaded project
renders a different scene and bypasses the per-prompt image reuse.
"""

import pytest

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)


class _FakeProject:
    def __init__(self) -> None:
        self.custom_visual_details: str | None = None


class _FakeDB:
    def __init__(self, project: object) -> None:
        self._project = project
        self.commits = 0

    async def get(self, _model: object, _pid: str) -> object:
        return self._project

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.unit
class TestAppendImageVisualFeedback:
    def _service(self) -> EditorialWorkflowService:
        # The helper uses no instance state; bypass the heavy DI constructor.
        return object.__new__(EditorialWorkflowService)

    async def test_first_feedback_sets_details(self) -> None:
        project = _FakeProject()
        db = _FakeDB(project)
        await self._service()._append_image_visual_feedback(
            db, "pid", "  make it brighter  "
        )
        assert project.custom_visual_details == "make it brighter"
        assert db.commits == 1

    async def test_subsequent_feedback_accumulates(self) -> None:
        project = _FakeProject()
        db = _FakeDB(project)
        svc = self._service()
        await svc._append_image_visual_feedback(db, "pid", "make it brighter")
        await svc._append_image_visual_feedback(db, "pid", "add a sunset")
        assert project.custom_visual_details is not None
        assert "make it brighter" in project.custom_visual_details
        assert "add a sunset" in project.custom_visual_details

    async def test_blank_feedback_is_ignored(self) -> None:
        project = _FakeProject()
        db = _FakeDB(project)
        await self._service()._append_image_visual_feedback(db, "pid", "   ")
        assert project.custom_visual_details is None
        assert db.commits == 0
