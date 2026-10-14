"""Secrets that must never reach a log line (QA r1 S-W2).

Telegram puts the bot token in the URL path and the Instagram Graph API
takes ``access_token`` as a query parameter. httpx logs request URLs at
INFO, so both its loggers are pinned to WARNING and every line is redacted.
"""

NOISY_HTTP_LOGGERS = ("httpx", "httpcore")
TELEGRAM_BOT_PATH_PATTERN = r"/bot\d+:[\w-]+"
TELEGRAM_BOT_PATH_REPLACEMENT = "/bot<redacted>"
GRAPH_QUERY_CREDENTIAL_PATTERN = r"access_token=[^&\s]+"
GRAPH_QUERY_CREDENTIAL_REPLACEMENT = "access_token=<redacted>"
