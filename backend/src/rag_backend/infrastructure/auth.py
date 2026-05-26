"""JWT authentication utilities."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from rag_backend.domain.constants import (
    ENCODING_UTF8,
    JWT_ALGORITHM,
    JWT_TYPE_ANON,
    JWT_TYPE_AUTH,
)
from rag_backend.domain.models import User
from rag_backend.infrastructure.config.settings import Settings


def create_access_token(
    settings: Settings,
    user: User,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token for an authenticated user.

    Args:
        settings: Application settings containing the secret key.
        user: The user to create the token for.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT token string.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": JWT_TYPE_AUTH,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=JWT_ALGORITHM
    )


def create_anonymous_token(
    settings: Settings,
    conversation_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token for an anonymous visitor.

    Args:
        settings: Application settings containing the secret key.
        conversation_id: The conversation ID for the anonymous session.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT token string.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.anon_token_expire_minutes)
    )
    payload = {
        "sub": f"anon:{conversation_id}",
        "conversation_id": conversation_id,
        "type": JWT_TYPE_ANON,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(
        payload, settings.anon_secret_key.get_secret_value(), algorithm=JWT_ALGORITHM
    )


def decode_access_token(settings: Settings, token: str) -> dict[str, object] | None:
    """Decode and validate an authenticated JWT access token.

    Args:
        settings: Application settings containing the secret key.
        token: The JWT token string to decode.

    Returns:
        Token payload dict if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key.get_secret_value(), algorithms=[JWT_ALGORITHM]
        )
        if payload.get("type") != JWT_TYPE_AUTH:
            return None
        return payload
    except jwt.PyJWTError:
        return None


def decode_anonymous_token(settings: Settings, token: str) -> dict[str, object] | None:
    """Decode and validate an anonymous JWT token.

    Args:
        settings: Application settings containing the anonymous secret key.
        token: The JWT token string to decode.

    Returns:
        Token payload dict if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.anon_secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
        )
        if payload.get("type") != JWT_TYPE_ANON:
            return None
        return payload
    except jwt.PyJWTError:
        return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password.

    Returns:
        Hashed password string.
    """
    password_bytes = password.encode(ENCODING_UTF8)[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode(ENCODING_UTF8)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to check against.

    Returns:
        True if the password matches, False otherwise.
    """
    plain_bytes = plain_password.encode(ENCODING_UTF8)[:72]
    hash_bytes = hashed_password.encode(ENCODING_UTF8)
    return bcrypt.checkpw(plain_bytes, hash_bytes)
