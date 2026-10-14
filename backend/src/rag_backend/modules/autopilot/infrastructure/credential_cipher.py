"""Fernet cipher for ``integration_credentials``. The key is never logged."""

from __future__ import annotations

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken as FernetInvalidToken

from rag_backend.modules.autopilot.constants import TEXT_ENCODING
from rag_backend.modules.autopilot.credential_constants import (
    KEY_PROBLEM_INVALID,
    KEY_PROBLEM_MISSING,
    LOG_CREDENTIAL_DECRYPT_FAILED,
)


class CredentialDecryptError(Exception):
    """Ciphertext could not be decrypted. The message is a constant."""

    def __init__(self) -> None:
        super().__init__(LOG_CREDENTIAL_DECRYPT_FAILED)


class FernetTokenCipher:
    """Encrypts and decrypts one provider token with ``CREDENTIALS_ENCRYPTION_KEY``."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(_key_bytes(key))

    def encrypt(self, plaintext: str) -> str:
        """Return URL-safe ciphertext. The plaintext is not retained."""
        raw = self._fernet.encrypt(plaintext.encode(TEXT_ENCODING))
        return raw.decode(TEXT_ENCODING)

    def decrypt(self, ciphertext: str) -> str:
        """Return the plaintext, or raise when the ciphertext does not match the key."""
        try:
            raw = self._fernet.decrypt(ciphertext.encode(TEXT_ENCODING))
        except (FernetInvalidToken, ValueError):
            raise CredentialDecryptError from None
        return raw.decode(TEXT_ENCODING)


def encryption_key_problem(key: str) -> str | None:
    """``missing`` or ``invalid``, or None when ``key`` can build a Fernet cipher."""
    if not key.strip():
        return KEY_PROBLEM_MISSING
    try:
        Fernet(_key_bytes(key))
    except (ValueError, TypeError):
        return KEY_PROBLEM_INVALID
    return None


def encryption_key_usable(key: str) -> bool:
    """True when autopilot Instagram publishing may use the encrypted store."""
    return encryption_key_problem(key) is None


def _key_bytes(key: str) -> bytes:
    return key.strip().encode(TEXT_ENCODING)
