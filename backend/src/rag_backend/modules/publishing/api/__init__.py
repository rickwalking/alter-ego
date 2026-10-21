"""API (inbound adapter) layer for the publishing bounded context.

Private to the module. The blog/publish/distribution/calendar/board/analytics
routes (and the public carousel→blog read endpoints) are NOT moved behind this
facade (scaffolding only); route delegation, the additive
``origin`` migration, persistence, distribution, the outbox, and the
carousel→blog projection land later.
"""
