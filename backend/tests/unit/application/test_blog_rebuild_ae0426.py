"""Selection + orchestration of the hidden-post rebuild.

Feature: backend/tests/features/blog_rebuild_hidden_ae0426.feature
The service runs against fake ports here; the SQL store + the blog generation pipeline
are exercised end to end in ``tests/integration/test_blog_rebuild_hidden``.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from uuid import UUID

from rag_backend.application.services.blog.blog_brief import CarouselMaterial
from rag_backend.application.services.blog.blog_generation_service import (
    GenerationJob,
)
from rag_backend.application.services.blog.blog_rebuild import (
    AttemptSpec,
    BlogRebuildService,
    RebuildCandidate,
    RebuildDeps,
    RebuildSelection,
    RebuiltStamp,
    selection_criterion,
)
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    LONG_FORM_NOTES_KEY,
)
from rag_backend.domain.constants.blog_document import BLOG_SCHEMA_V2
from rag_backend.domain.constants.blog_rebuild import (
    CRITERION_ALREADY_REBUILT,
    CRITERION_CURRENTLY_PUBLISHED,
    CRITERION_MARKER,
    CRITERION_MISSING_CAROUSEL,
    CRITERION_MISSING_NOTES,
    CRITERION_V2_WITH_QUALITY,
    OUTCOME_FAILED,
    REBUILD_ACTOR,
)
from rag_backend.domain.models.blog_generation import (
    GenerationLease,
    GenerationOutcome,
)
from rag_backend.domain.models.carousel import CarouselSlide
from rag_backend.domain.models.persona import PersonaProfile

POST_A = "post-a"
POST_B = "post-b"
POST_C = "post-c"
POST_D = "post-d"
PROJECT_A = "11111111-1111-1111-1111-111111111111"


def _candidate(post_id: str, **overrides: object) -> RebuildCandidate:
    base = RebuildCandidate(
        post_id=post_id,
        project_id=PROJECT_A,
        author_id="author-1",
        lock_version=3,
        status="draft",
        has_hidden_marker=True,
        rebuilt_at=None,
        content_schema=None,
        voice_score=None,
    )
    return dataclasses.replace(base, **overrides)


@dataclass
class _FakeStore:
    rows: list[RebuildCandidate]
    deny_lease: set[str] = field(default_factory=set)
    mark_error_on: set[str] = field(default_factory=set)
    started: list[AttemptSpec] = field(default_factory=list)
    stamped: list[RebuiltStamp] = field(default_factory=list)

    async def candidates(self) -> list[RebuildCandidate]:
        return list(self.rows)

    async def start_attempt(self, spec: AttemptSpec) -> GenerationLease | None:
        self.started.append(spec)
        if spec.post_id in self.deny_lease:
            return None
        return GenerationLease(
            post_id=spec.post_id,
            lease_id=spec.start.lease_id,
            lock_version=spec.seen_lock_version + 1,
        )

    async def mark_rebuilt(self, stamp: RebuiltStamp) -> None:
        if stamp.post_id in self.mark_error_on:
            raise RuntimeError("stamp failed")
        self.stamped.append(stamp)


@dataclass
class _FakeMaterials:
    materials: dict[str, CarouselMaterial | None]
    loaded: list[str] = field(default_factory=list)
    error_on: set[str] = field(default_factory=set)

    async def load(self, candidate: RebuildCandidate) -> CarouselMaterial | None:
        self.loaded.append(candidate.post_id)
        if candidate.post_id in self.error_on:
            raise RuntimeError("materials unavailable")
        return self.materials.get(candidate.post_id)


@dataclass
class _FakeRunner:
    status: str = "complete"
    jobs: list[GenerationJob] = field(default_factory=list)

    async def run(self, job: GenerationJob) -> GenerationOutcome | None:
        self.jobs.append(job)
        return GenerationOutcome(status=self.status)


@dataclass
class _FlakyRunner(_FakeRunner):
    """Fails the first post it sees, then behaves like ``_FakeRunner``."""

    fail_post: str = POST_A

    async def run(self, job: GenerationJob) -> GenerationOutcome | None:
        if job.lease.post_id == self.fail_post:
            raise RuntimeError("boom")
        return await super().run(job)


def _slide(notes: str | None = "Nota 1") -> CarouselSlide:
    extras = {LONG_FORM_NOTES_KEY: notes} if notes is not None else {}
    return CarouselSlide(
        project_id=UUID(PROJECT_A),
        slide_number=1,
        slide_type="content",
        heading="Slide",
        body="corpo",
        extras=extras,
    )


def _material(notes: bool = True) -> CarouselMaterial:
    return CarouselMaterial(
        title="T",
        topic="t",
        persona=PersonaProfile(name="Pedro"),
        section_count=3,
        slides=(_slide() if notes else _slide(notes=None),),
    )


def _service(
    store: _FakeStore,
    materials: _FakeMaterials,
    runner: _FakeRunner,
) -> BlogRebuildService:
    return BlogRebuildService(
        RebuildDeps(
            store=store,
            materials=materials,
            service_factory=lambda _persona, _user_id: runner,
            clock=lambda: "2026-10-18T00:00:00+00:00",
            new_lease=lambda: "lease-1",
        )
    )


# Scenario: Dry-run lists the marker-selected rows
async def test_preview_lists_marker_rows_and_skips_the_rest() -> None:
    store = _FakeStore(
        rows=[
            _candidate(POST_A),
            _candidate(POST_B, has_hidden_marker=False),
            _candidate(POST_C, rebuilt_at="2026-10-18"),
            _candidate(POST_D, content_schema=BLOG_SCHEMA_V2, voice_score=88.0),
        ]
    )
    service = _service(store, _FakeMaterials({POST_A: _material()}), _FakeRunner())
    report = await service.preview()
    assert [entry.post_id for entry in report.selected] == [POST_A]
    assert {entry.post_id for entry in report.skipped} == {POST_C, POST_D}
    assert store.started == []
    assert report.counts == {"selected": 1, "rebuilt": 0, "skipped": 2, "failed": 0}


# Scenario: Dry-run reports missing carousel/notes without a paid generation
async def test_preview_reports_missing_material_without_running() -> None:
    store = _FakeStore(
        rows=[_candidate(POST_A), _candidate(POST_B), _candidate(POST_C)]
    )
    materials = _FakeMaterials({
        POST_A: None,
        POST_B: _material(notes=False),
        POST_C: _material(),
    })
    runner = _FakeRunner()
    report = await _service(store, materials, runner).preview()
    assert [entry.post_id for entry in report.selected] == [POST_C]
    assert {entry.criterion for entry in report.skipped} == {
        CRITERION_MISSING_CAROUSEL,
        CRITERION_MISSING_NOTES,
    }
    assert runner.jobs == []
    assert {entry.post_id for entry in report.skipped} == {POST_A, POST_B}


# Scenario: A target row is rebuilt as a draft
async def test_run_rebuilds_a_selected_row() -> None:
    store = _FakeStore(rows=[_candidate(POST_A)])
    materials = _FakeMaterials({POST_A: _material()})
    report = await _service(store, materials, _FakeRunner()).run()
    assert store.started[0].post_id == POST_A
    assert store.started[0].seen_lock_version == 3
    assert store.stamped[0].status == "complete"
    assert store.stamped[0].at == "2026-10-18T00:00:00+00:00"
    assert [entry.post_id for entry in report.rebuilt] == [POST_A]


# Scenario: The rebuild never publishes
async def test_run_only_starts_attempts_and_stamps() -> None:
    store = _FakeStore(rows=[_candidate(POST_A)])
    await _service(store, _FakeMaterials({POST_A: _material()}), _FakeRunner()).run()
    assert len(store.started) == 1
    assert len(store.stamped) == 1


# Scenario: Re-running the script is a no-op
async def test_rebuilt_row_is_not_attempted_again() -> None:
    store = _FakeStore(rows=[_candidate(POST_A, rebuilt_at="2026-10-18")])
    report = await _service(store, _FakeMaterials({}), _FakeRunner()).run()
    assert store.started == []
    assert report.skipped[0].criterion == CRITERION_ALREADY_REBUILT


# Scenario: A missing carousel is reported and skipped
async def test_missing_carousel_is_skipped() -> None:
    store = _FakeStore(rows=[_candidate(POST_A)])
    report = await _service(store, _FakeMaterials({POST_A: None}), _FakeRunner()).run()
    assert store.started == []
    assert report.skipped[0].criterion == CRITERION_MISSING_CAROUSEL
    assert report.failed == []


# Scenario: A carousel without long_form_notes is not rebuilt
async def test_missing_notes_is_skipped() -> None:
    store = _FakeStore(rows=[_candidate(POST_A)])
    report = await _service(
        store, _FakeMaterials({POST_A: _material(notes=False)}), _FakeRunner()
    ).run()
    assert store.started == []
    assert report.skipped[0].criterion == CRITERION_MISSING_NOTES


# Scenario: A published row is not silently unpublished
async def test_published_row_is_skipped_unless_allowed() -> None:
    store = _FakeStore(rows=[_candidate(POST_A, status="published")])
    materials = _FakeMaterials({POST_A: _material()})
    report = await _service(store, materials, _FakeRunner()).run()
    assert store.started == []
    assert report.skipped[0].criterion == CRITERION_CURRENTLY_PUBLISHED

    allowed = _FakeStore(rows=[_candidate(POST_A, status="published")])
    report = await _service(allowed, materials, _FakeRunner()).run(
        RebuildSelection(allow_published=True)
    )
    assert allowed.started != []
    assert allowed.started[0].allow_published is True
    assert [entry.post_id for entry in report.rebuilt] == [POST_A]


# Scenario: The operator narrows the run with --only/--limit/--max-posts
async def test_selection_only_limit_and_max_posts() -> None:
    rows = [_candidate(post_id) for post_id in (POST_A, POST_B, POST_C, POST_D)]
    materials = _FakeMaterials({
        post_id: _material() for post_id in (POST_A, POST_B, POST_C, POST_D)
    })
    only = _service(_FakeStore(rows=rows), materials, _FakeRunner())
    report = await only.run(RebuildSelection(only=frozenset({POST_C})))
    assert [entry.post_id for entry in report.selected] == [POST_C]

    limited = _service(_FakeStore(rows=rows), materials, _FakeRunner())
    report = await limited.run(RebuildSelection(limit=2))
    assert [entry.post_id for entry in report.selected] == [POST_A, POST_B]
    assert report.omitted == 2

    capped = _FakeStore(rows=rows)
    report = await _service(capped, materials, _FakeRunner()).run(
        RebuildSelection(max_posts=1)
    )
    assert len(capped.started) == 1
    assert report.counts["selected"] == 1
    assert report.omitted == 3


async def test_preview_ignores_the_apply_spend_cap() -> None:
    rows = [_candidate(post_id) for post_id in (POST_A, POST_B, POST_C)]
    materials = _FakeMaterials({row.post_id: _material() for row in rows})
    report = await _service(_FakeStore(rows=rows), materials, _FakeRunner()).preview(
        RebuildSelection(max_posts=1)
    )
    assert len(report.selected) == 3
    assert report.omitted == 0


# Scenario: A per-post failure does not abort the run
async def test_one_failure_does_not_abort_the_run() -> None:
    store = _FakeStore(rows=[_candidate(POST_A), _candidate(POST_B)])
    materials = _FakeMaterials({POST_A: _material(), POST_B: _material()})
    runner = _FlakyRunner()
    report = await _service(store, materials, runner).run()
    assert [entry.post_id for entry in report.failed] == [POST_A]
    assert report.failed[0].detail == "RuntimeError"
    assert [entry.post_id for entry in report.rebuilt] == [POST_B]
    assert {stamp.post_id for stamp in store.stamped} == {POST_B}


# Scenario: Material/stamp errors are isolated too (not just the generator)
async def test_material_and_stamp_errors_do_not_abort_the_run() -> None:
    store = _FakeStore(
        rows=[_candidate(POST_A), _candidate(POST_B), _candidate(POST_C)],
        mark_error_on={POST_B},
    )
    materials = _FakeMaterials(
        {POST_A: _material(), POST_B: _material(), POST_C: _material()},
        error_on={POST_A},
    )
    report = await _service(store, materials, _FakeRunner()).run()
    assert {entry.post_id for entry in report.failed} == {POST_A, POST_B}
    assert [entry.post_id for entry in report.rebuilt] == [POST_C]


# Scenario: partial images are still a rebuild; a lost lease is a failure
async def test_partial_is_rebuilt_but_failed_outcome_is_not_stamped() -> None:
    store = _FakeStore(rows=[_candidate(POST_A)])
    runner = _FakeRunner(status="partial")
    report = await _service(store, _FakeMaterials({POST_A: _material()}), runner).run()
    assert store.stamped[0].status == "partial"
    assert [entry.post_id for entry in report.rebuilt] == [POST_A]

    lost = _FakeStore(rows=[_candidate(POST_A)], deny_lease={POST_A})
    report = await _service(
        lost, _FakeMaterials({POST_A: _material()}), _FakeRunner()
    ).run()
    assert lost.stamped == []
    assert report.failed[0].criterion == OUTCOME_FAILED


# Scenario: The run builds the service for the row's author (or the audit actor)
async def test_service_and_trace_use_the_author_or_the_audit_actor() -> None:
    store = _FakeStore(rows=[_candidate(POST_A), _candidate(POST_B, author_id=None)])
    materials = _FakeMaterials({POST_A: _material(), POST_B: _material()})
    runner = _FakeRunner()
    calls: list[tuple[str, str]] = []

    def factory(persona: PersonaProfile, user_id: str) -> _FakeRunner:
        calls.append((persona.name, user_id))
        return runner

    service = BlogRebuildService(
        RebuildDeps(
            store=store,
            materials=materials,
            service_factory=factory,
            clock=lambda: "2026-10-18T00:00:00+00:00",
            new_lease=lambda: "lease-1",
        )
    )
    await service.run(RebuildSelection(max_posts=None))
    assert calls == [("Pedro", "author-1"), ("Pedro", REBUILD_ACTOR)]
    assert [job.trace.user_id for job in runner.jobs] == ["author-1", REBUILD_ACTOR]
    assert all(job.retitle for job in runner.jobs)


def test_selection_criterion_reports_reasons() -> None:
    assert selection_criterion(_candidate(POST_A)) == CRITERION_MARKER
    assert (
        selection_criterion(_candidate(POST_A, rebuilt_at="x"))
        == CRITERION_ALREADY_REBUILT
    )
    assert (
        selection_criterion(_candidate(POST_A, status="published"))
        == CRITERION_CURRENTLY_PUBLISHED
    )
    assert (
        selection_criterion(
            _candidate(POST_A, status="published"), allow_published=True
        )
        == CRITERION_MARKER
    )
    assert (
        selection_criterion(
            _candidate(POST_A, content_schema=BLOG_SCHEMA_V2, voice_score=70.0)
        )
        == CRITERION_V2_WITH_QUALITY
    )
    assert (
        selection_criterion(
            _candidate(POST_A, content_schema=BLOG_SCHEMA_V2, voice_score=None)
        )
        == CRITERION_MARKER
    )
    assert selection_criterion(_candidate(POST_A, has_hidden_marker=False)) is None
