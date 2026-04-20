"""JWT authentication utilities."""

from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from rag_backend.infrastructure.config.settings import Settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(
    settings: Settings,
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        settings: Application settings containing the secret key.
        subject: The token subject (typically user ID or API key identifier).
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT token string.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(settings: Settings, token: str) -> dict | None:
    """Decode and validate a JWT access token.

    Args:
        settings: Application settings containing the secret key.
        token: The JWT token string to decode.

    Returns:
        Token payload dict if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
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
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to check against.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
