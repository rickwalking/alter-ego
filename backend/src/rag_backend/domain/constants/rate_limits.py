"""Rate limit constants for API endpoints."""

RATE_LIMIT_AI_ENDPOINTS = "10/minute"
RATE_LIMIT_SSE_STREAM = "30/minute"
RATE_LIMIT_WORKFLOW_ENDPOINTS = "60/minute"
RATE_LIMIT_CAROUSEL_PUBLISH = "20/minute"
RATE_LIMIT_ADMIN_MIGRATION = "2/minute"
# AE-0270: throttle palette mutations (create/edit/archive) to curb catalog spam
# (skeptical G5 — creation abuse) and AUTO-keyword poisoning.
RATE_LIMIT_PALETTE_WRITE = "10/minute"
# AE-0297: public unauthenticated blog reads - committed abuse ceiling
# (<=120/min/IP per the external review; distributed scraping = WAF follow-up).
RATE_LIMIT_PUBLIC_BLOG_READ = "120/minute"

__all__ = [
    "RATE_LIMIT_ADMIN_MIGRATION",
    "RATE_LIMIT_AI_ENDPOINTS",
    "RATE_LIMIT_CAROUSEL_PUBLISH",
    "RATE_LIMIT_PALETTE_WRITE",
    "RATE_LIMIT_PUBLIC_BLOG_READ",
    "RATE_LIMIT_SSE_STREAM",
    "RATE_LIMIT_WORKFLOW_ENDPOINTS",
]
