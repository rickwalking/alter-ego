"""Content calendar entry types (the ``content_type`` of a calendar item)."""

from typing import Final, Literal

CALENDAR_CONTENT_TYPE_BLOG_POST: Final = "blog_post"
CALENDAR_CONTENT_TYPE_CAROUSEL: Final = "carousel"

CalendarContentType = Literal["blog_post", "carousel"]

__all__ = [
    "CALENDAR_CONTENT_TYPE_BLOG_POST",
    "CALENDAR_CONTENT_TYPE_CAROUSEL",
    "CalendarContentType",
]
