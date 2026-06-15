"""API (inbound adapter) layer for the presentation bounded context.

Private to the module. The carousel presentation routes (design/blog/slide/
strategy/creator-asset responses, artifact URLs, ``FileResponse`` bytes) are NOT
moved behind this facade in AE-0117 (scaffolding only); route delegation is a
later phase (AE-0120).
"""
