"""Authentication & authorization constants."""

ROLE_ADMIN = "admin"
ROLE_EDITOR = "editor"
VALID_ROLES: set[str] = {ROLE_ADMIN, ROLE_EDITOR}

MIN_PASSWORD_LENGTH = 12

JWT_ALGORITHM = "HS256"
JWT_TYPE_AUTH = "auth"
JWT_TYPE_ANON = "anon"

COOKIE_ACCESS_TOKEN = "access_token"  # noqa: S105 — not a password, cookie name
COOKIE_ANON_TOKEN = "anon_token"  # noqa: S105 — not a password, cookie name
