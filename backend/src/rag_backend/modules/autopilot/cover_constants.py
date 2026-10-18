"""Autopilot constants for the GrokBot slide-1 cover (AE-0418, ADR-0024).

Contract: ``docs/architecture/grokbot-cover-asset.md``. The scout uploads a
cover through ``POST /api/autopilot/assets`` and names it on a topic
(``cover.asset_id``). Slide 1 keeps its default until the owner taps
"Usar capa do Grok" on Telegram; the reason codes are public, never rename them.
"""

from __future__ import annotations

from rag_backend.domain.constants.slide_cover import (
    ERR_COVER_ASSET_KIND_INVALID,
    ERR_COVER_ASSET_SOURCE_MISSING,
    ERR_COVER_ASSET_TOO_LARGE,
    ERR_COVER_ASSET_TOO_SMALL,
    ERR_COVER_ASSET_TYPE_UNSUPPORTED,
)

PATH_ASSETS = "/assets"
FORM_FIELD_FILE = "file"
FORM_FIELD_KIND = "kind"
FORM_FIELD_SOURCE_URL = "source_url"
# Read one byte past the 5 MB cap so an oversized body is detected, not stored.
UPLOAD_READ_SLACK_BYTES = 1

# HTTP status per upload code (contract §3; Decision Log D3).
HTTP_PAYLOAD_TOO_LARGE = 413
HTTP_UNSUPPORTED_MEDIA_TYPE = 415
HTTP_UNPROCESSABLE = 422
HTTP_UNAVAILABLE = 503
UPLOAD_STATUS_BY_CODE: dict[str, int] = {
    ERR_COVER_ASSET_TOO_LARGE: HTTP_PAYLOAD_TOO_LARGE,
    ERR_COVER_ASSET_TYPE_UNSUPPORTED: HTTP_UNSUPPORTED_MEDIA_TYPE,
    ERR_COVER_ASSET_TOO_SMALL: HTTP_UNPROCESSABLE,
    ERR_COVER_ASSET_KIND_INVALID: HTTP_UNPROCESSABLE,
    ERR_COVER_ASSET_SOURCE_MISSING: HTTP_UNPROCESSABLE,
}
# No owner user configured: the cover has nobody to belong to (server-side).
DETAIL_COVER_OWNER_UNCONFIGURED = "autopilot_owner_unconfigured"

# Topic field ``cover`` (contract §4): per-topic rejections.
FIELD_COVER_ASSET_ID = "cover.asset_id"
COVER_ASSET_ID_MAX_CHARS = 64
REASON_COVER_ASSET_UNKNOWN = "cover_asset_unknown"
REASON_COVER_ASSET_EXPIRED = "cover_asset_expired"
REASON_COVER_ASSET_USED = "cover_asset_used"
REASON_COVER_SOURCE_INVALID = "cover_source_invalid"
# An unused cover may be attached for 6 hours, then the sweep deletes it.
COVER_MAX_AGE_HOURS = 6
COVER_SWEEP_LIMIT = 20

# Table ``autopilot_cover_assets``.
TABLE_COVER_ASSETS = "autopilot_cover_assets"
FK_COVER_CREATOR_ASSET = "fk_autopilot_cover_assets_creator_asset"
FK_COVER_TOPIC = "fk_autopilot_cover_assets_topic"
INDEX_COVER_CREATED_AT = "ix_autopilot_cover_assets_created_at"
CREATOR_ASSET_FK = "carousel_creator_assets.id"
COVER_TOPIC_FK = "topic_candidates.id"
COVER_UUID_CHARS = 36
COVER_SOURCE_URL_MAX_CHARS = 2048

# Telegram: ``ap:cv:<run>`` uses the cover, ``ap:cvoff:<run>`` drops it.
KIND_COVER_ON = "cv"
CALLBACK_COVER_ON_PREFIX = "ap:cv:"
CALLBACK_COVER_OFF_PREFIX = "ap:cvoff:"
CALLBACK_COVER_PATTERN = (
    r"^ap:(cv|cvoff):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)
BUTTON_COVER_ON = "🖼️ Usar capa do Grok"
BUTTON_COVER_OFF_POV = "📸 Usar minha foto"
BUTTON_COVER_OFF_NEWS = "↩️ Usar capa padrão"
CAPTION_COVER_AI_IMAGE = "🖼️ Capa do Grok (imagem gerada) para o slide 1 deste post."
CAPTION_COVER_SCREENSHOT = (
    "🖼️ Capa do Grok (print da fonte, {credit}) para o slide 1 deste post."
)
ANSWER_COVER_ON = "Slide 1: capa do Grok"
ANSWER_COVER_OFF = "Slide 1: capa padrão"
ANSWER_COVER_SAME = "Já está assim"
ANSWER_COVER_NOT_NOW = "A capa não pode mudar agora"
TEXT_COVER_SWITCHING = "🖼️ Trocando a capa do slide 1. A revisão volta em instantes."
# The rework marker the worker tick reads (fits REWORK_PHASE_LENGTH).
COVER_REWORK_PHASE = "owner_cover"
REASON_COVER_SWITCH = "owner_cover_switch"
REASON_COVER_MISSING = "cover_file_missing"
# The slide-1 switch was stored but the re-render failed: escalated, not done.
REASON_COVER_RENDER_FAILED = "cover_render_failed"
TEXT_COVER_RENDER_FAILED = (
    "🖼️ A troca da capa do slide 1 não renderizou. Os slides não mudaram; "
    "abra o carrossel no dashboard e gere de novo."
)
# Notice-ledger key: the thesis-time cover photo is sent once per run.
COVER_NOTICE_KEY = "cover:{scope}:{run_id}"
COVER_SCOPE_THESIS = "thesis"

LOG_COVER = "autopilot.cover"
LOG_COVER_UPLOADED = "uploaded"
LOG_COVER_REJECTED = "rejected"
LOG_COVER_SWEPT = "swept"
LOG_COVER_PHOTO_FAILED = "photo_failed"
LOG_COVER_RENDER_FAILED = "render_failed"

__all__ = [
    "ANSWER_COVER_NOT_NOW",
    "ANSWER_COVER_OFF",
    "ANSWER_COVER_ON",
    "ANSWER_COVER_SAME",
    "BUTTON_COVER_OFF_NEWS",
    "BUTTON_COVER_OFF_POV",
    "BUTTON_COVER_ON",
    "CALLBACK_COVER_OFF_PREFIX",
    "CALLBACK_COVER_ON_PREFIX",
    "CALLBACK_COVER_PATTERN",
    "CAPTION_COVER_AI_IMAGE",
    "CAPTION_COVER_SCREENSHOT",
    "COVER_ASSET_ID_MAX_CHARS",
    "COVER_MAX_AGE_HOURS",
    "COVER_NOTICE_KEY",
    "COVER_REWORK_PHASE",
    "COVER_SCOPE_THESIS",
    "COVER_SOURCE_URL_MAX_CHARS",
    "COVER_SWEEP_LIMIT",
    "COVER_TOPIC_FK",
    "COVER_UUID_CHARS",
    "CREATOR_ASSET_FK",
    "DETAIL_COVER_OWNER_UNCONFIGURED",
    "FIELD_COVER_ASSET_ID",
    "FK_COVER_CREATOR_ASSET",
    "FK_COVER_TOPIC",
    "FORM_FIELD_FILE",
    "FORM_FIELD_KIND",
    "FORM_FIELD_SOURCE_URL",
    "HTTP_PAYLOAD_TOO_LARGE",
    "HTTP_UNAVAILABLE",
    "HTTP_UNPROCESSABLE",
    "HTTP_UNSUPPORTED_MEDIA_TYPE",
    "INDEX_COVER_CREATED_AT",
    "KIND_COVER_ON",
    "LOG_COVER",
    "LOG_COVER_PHOTO_FAILED",
    "LOG_COVER_REJECTED",
    "LOG_COVER_RENDER_FAILED",
    "LOG_COVER_SWEPT",
    "LOG_COVER_UPLOADED",
    "PATH_ASSETS",
    "REASON_COVER_ASSET_EXPIRED",
    "REASON_COVER_ASSET_UNKNOWN",
    "REASON_COVER_ASSET_USED",
    "REASON_COVER_MISSING",
    "REASON_COVER_RENDER_FAILED",
    "REASON_COVER_SOURCE_INVALID",
    "REASON_COVER_SWITCH",
    "TABLE_COVER_ASSETS",
    "TEXT_COVER_RENDER_FAILED",
    "TEXT_COVER_SWITCHING",
    "UPLOAD_READ_SLACK_BYTES",
    "UPLOAD_STATUS_BY_CODE",
]
