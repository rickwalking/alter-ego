"""Settings-backed Instagram token until AE-0358 stores it encrypted."""

from __future__ import annotations

from pydantic import SecretStr


class StaticInstagramTokenProvider:
    """Reads the token injected at startup. The plaintext is not logged."""

    def __init__(self, access_token: SecretStr | str) -> None:
        self._access_token = access_token

    async def get(self) -> str:
        """Return the configured token, or an empty string when unset."""
        token = self._access_token
        if isinstance(token, SecretStr):
            return token.get_secret_value()
        return token
