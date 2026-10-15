"""A ``ProjectInputs`` fake for runner tests (PR #106 review).

Defaults to a configured persona and a usable slide-1 photo, so a POV run can
start; a test passes ``None`` to exercise the missing-persona / missing-photo
paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field

FAKE_PERSONA_ID = "persona-pedro"
FAKE_HOOK_ASSET_ID = "00000000-0000-4000-8000-0000000000aa"


@dataclass
class FakeProjectInputs:
    """Returns fixed ids and records the owners it was asked about."""

    persona: str | None = FAKE_PERSONA_ID
    hook: str | None = FAKE_HOOK_ASSET_ID
    hook_owners: list[str] = field(default_factory=list)

    async def persona_id(self) -> str | None:
        return self.persona

    async def hook_photo_id(self, owner_user_id: str) -> str | None:
        self.hook_owners.append(owner_user_id)
        return self.hook
