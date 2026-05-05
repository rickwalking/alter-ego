"""Background graph execution for the carousel pipeline.

Each function takes ``self`` (a CarouselAgent instance) as the first param
so they can be assigned as methods on the class at definition time.
"""

import asyncio
from uuid import UUID

from rag_backend.application.services.carousel.graph import build_graph
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.domain.types import PipelineEvent
from rag_backend.infrastructure.logging import get_logger

from ._constants import _ERR_PROJECT_NOT_FOUND

logger = get_logger()


async def _run_graph_body(
    self,
    project_id: UUID,
    seed_urls: list[str] | None,
    queue: asyncio.Queue[PipelineEvent],
    repo: CarouselRepository,
) -> None:
    project = await repo.get_project_by_id(project_id)
    if project is None:
        await queue.put(
            {
                "node": "error",
                "status": "failed",
                "phase_progress": None,
                "error": _ERR_PROJECT_NOT_FOUND.format(project_id),
            }
        )
        return

    output_dir = self._output_base / str(project_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    graph = build_graph(self._build_deps(repo=repo), checkpointer=self._checkpointer)
    initial_state: PipelineState = {
        "project_id": project_id,
        "seed_urls": seed_urls or [],
        "output_dir": str(output_dir),
        "project": project,
    }
    config = (
        {"configurable": {"thread_id": self._thread_id(project_id)}}
        if self._checkpointer is not None
        else None
    )

    await queue.put(
        {
            "node": "start",
            "status": project.status.value,
            "phase_progress": project.phase_progress,
        }
    )

    has_checkpoint = False
    if config is not None:
        try:
            snapshot = await graph.aget_state(config)
            has_checkpoint = snapshot is not None and bool(snapshot.values)
        except Exception:
            has_checkpoint = False

    try:
        stream_input = None if has_checkpoint else initial_state
        async for update in graph.astream(stream_input, config=config):
            for node_name, partial in update.items():
                snapshot = partial.get("project") if isinstance(partial, dict) else None
                if snapshot is None:
                    continue
                await queue.put(
                    {
                        "node": node_name,
                        "status": snapshot.status.value,
                        "phase_progress": snapshot.phase_progress,
                    }
                )
    except Exception as exc:
        latest_project = await repo.get_project_by_id(project_id)
        if latest_project is None:
            latest_project = project
        latest_project.mark_failed(str(exc))
        await repo.update_project(latest_project)
        await queue.put(
            {
                "node": "error",
                "status": latest_project.status.value,
                "phase_progress": latest_project.phase_progress,
                "error": str(exc),
            }
        )
        return

    final_project = await repo.get_project_by_id(project_id)
    await queue.put(
        {
            "node": "end",
            "status": final_project.status.value if final_project else "completed",
            "phase_progress": final_project.phase_progress if final_project else None,
        }
    )


async def _run_graph_producer(
    self,
    project_id: UUID,
    seed_urls: list[str] | None,
    queue: asyncio.Queue[PipelineEvent],
) -> None:
    if self._session_maker is not None and self._repository_factory is not None:
        async with self._session_maker() as session:
            repo = self._repository_factory(session)
            await self._run_graph_body(project_id, seed_urls, queue, repo)
    else:
        await self._run_graph_body(project_id, seed_urls, queue, self._repo)
