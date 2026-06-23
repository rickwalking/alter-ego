"""PostgreSQL repository for the global custom-palette catalog (AE-0269)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models.palette import CustomPalette
from rag_backend.domain.protocols.palette import PaletteRepository
from rag_backend.infrastructure.database.models.palette import PaletteModel


class PostgresPaletteRepository(PaletteRepository):
    """PostgreSQL implementation of the ``PaletteRepository`` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, palette_id: UUID) -> CustomPalette | None:
        result = await self._session.execute(
            select(PaletteModel).where(PaletteModel.id == palette_id)
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row is not None else None

    async def list_active(self) -> list[CustomPalette]:
        result = await self._session.execute(
            select(PaletteModel).where(PaletteModel.archived.is_(False))
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def add(self, palette: CustomPalette) -> CustomPalette:
        # Flush (not commit) so uniqueness conflicts surface as IntegrityError
        # here while the caller keeps ownership of the transaction boundary.
        model = PaletteModel.from_domain(palette)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_domain()

    async def update(self, palette: CustomPalette) -> CustomPalette:
        result = await self._session.execute(
            select(PaletteModel).where(PaletteModel.id == palette.id)
        )
        row = result.scalar_one()
        # Slug is immutable (D8) — intentionally not copied from the entity.
        row.name = palette.name
        row.primary = palette.palette.primary
        row.accent = palette.palette.accent
        row.background = palette.palette.background
        row.mode = palette.mode.value
        row.keywords = list(palette.keywords)
        row.archived = palette.archived
        await self._session.flush()
        await self._session.refresh(row)
        return row.to_domain()

    async def archive(self, palette_id: UUID) -> bool:
        result = await self._session.execute(
            select(PaletteModel).where(PaletteModel.id == palette_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.archived = True
        await self._session.flush()
        return True
