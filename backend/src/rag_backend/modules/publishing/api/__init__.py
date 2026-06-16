"""API (inbound adapter) layer for the publishing bounded context.

Private to the module. The blog/publish/distribution/calendar/board/analytics
routes (and the public carousel→blog read endpoints) are NOT moved behind this
facade in AE-0126 (scaffolding only); route delegation, the additive
``origin`` migration, persistence, distribution, the outbox, and the
carousel→blog projection land in AE-0127..0131.
"""
