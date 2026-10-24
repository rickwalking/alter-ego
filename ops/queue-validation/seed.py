"""Seed the validation stack: the owner, the persona and N queued Radar IA runs.

Runs with the backend's Python and environment (``rag_backend`` importable,
``DATABASE_URL`` and ``AUTOPILOT_OWNER_USER_ID`` set). The topics and their queued
autopilot runs are written the way the topic intake leaves them, without the
intake's weekly Radar IA cap, so one batch can load the queue with several
themes. Every topic source points at the mock's article pages.

Usage: ``python seed.py <count>`` (``SEED_OFFSET`` shifts the theme numbers for a
second batch). Prints the queued autopilot run ids as JSON.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import get_session_maker, init_db
from rag_backend.infrastructure.database.models.persona_rubric import (
    PersonaProfileModel,
)
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)

PERSONA_NAME = "Pedro"
OFFSET = int(os.environ.get("SEED_OFFSET", "0"))
SOURCE_URL = os.environ.get("SEED_SOURCE_URL", "http://llm-mock:8080/article/{n}")
SUBJECTS = (
    ("Agentes de IA", "revisão de código"),
    ("Modelos abertos", "custos de inferência"),
    ("Assistentes de voz", "atendimento ao cliente"),
    ("Visão computacional", "controle de qualidade"),
    ("Busca semântica", "documentação interna"),
    ("Robôs de armazém", "logística urbana"),
    ("Tradução automática", "suporte multilíngue"),
    ("Geração de imagens", "campanhas de marketing"),
    ("Chips dedicados", "data centers"),
    ("Copilotos jurídicos", "contratos simples"),
)


def topic_row(index: int, now: datetime) -> TopicCandidateModel:
    """One accepted Radar IA topic whose sources are mock articles."""
    subject, field = SUBJECTS[index % len(SUBJECTS)]
    title = f"{subject} mudam {field}"
    return TopicCandidateModel(
        id=uuid.uuid4(),
        title=title,
        angle=f"O que muda quando {subject.lower()} entram em {field}",
        why_viral=f"Times querem saber se {subject.lower()} cortam custo de verdade",
        audience="devs",
        niche="ai",
        brief=f"{subject}: ganhos medidos e limites reais em {field}.",
        sources=[SOURCE_URL.format(n=index * 3 + k) for k in range(3)],
        score=90,
        signal_hash=hashlib.sha256(f"{title}-{now.isoformat()}".encode()).hexdigest(),
        status="accepted",
        created_at=now,
    )


async def seed(count: int) -> list[str]:
    """Owner, persona, then ``count`` topics with a queued run each."""
    settings = get_settings()
    await init_db(settings.database_url)
    owner_id = settings.autopilot_owner_user_id
    now = datetime.now(UTC)
    run_ids: list[str] = []
    async with get_session_maker()() as session:
        if await session.get(UserModel, owner_id) is None:
            session.add(
                UserModel(
                    id=owner_id,
                    email="owner@validation.invalid",
                    full_name="Validation Owner",
                    hashed_password="not-used",
                    role="admin",
                )
            )
        persona = await session.scalar(
            select(PersonaProfileModel.id).where(PersonaProfileModel.name == PERSONA_NAME)
        )
        if persona is None:
            session.add(
                PersonaProfileModel(
                    id=str(uuid.uuid4()),
                    name=PERSONA_NAME,
                    description="Validation persona",
                    writing_samples=["Texto curto, direto, com dados."],
                    forbidden_phrases=[],
                    preferred_phrases=[],
                    expertise_areas=["ai"],
                )
            )
        for index in range(OFFSET, OFFSET + count):
            topic = topic_row(index, now)
            session.add(topic)
            await session.flush()
            run_id = uuid.uuid4()
            session.add(
                AutopilotRunModel(
                    id=run_id,
                    topic_candidate_id=topic.id,
                    state="queued",
                    publish_attempts=0,
                    start_attempts=0,
                    telegram_message_ids=[],
                    created_at=now,
                    updated_at=now,
                )
            )
            run_ids.append(str(run_id))
        await session.commit()
    return run_ids


if __name__ == "__main__":
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(json.dumps(asyncio.run(seed(total))))
