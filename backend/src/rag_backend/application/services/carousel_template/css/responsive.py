"""Neon Shell v2.0 responsive and accessibility CSS."""

from __future__ import annotations


def _get_neon_responsive_css() -> str:
    """Return responsive breakpoint and reduced-motion CSS matching reference."""
    return """
  @media (max-width: 640px) {
    .feed { padding: 0 0 40px; }
    .slide-content { padding: 28px 20px 24px; }
    .slide-1-content { padding: 24px 20px 56px; }
    .slide-1-bg-img img { object-position: center 20%; }
    .stat-row { gap: 5px; }
    .stat-card { padding: 8px 4px; }
    .feature-item { padding: 7px 10px; }
    .feature-grid.cols-2 { grid-template-columns: 1fr; }
    .summary-grid { grid-template-columns: 1fr; }
    .hero-img { height: 100px; }
    .page-header { padding: 32px 16px 16px; }
    .creator-watermark { bottom: 10px; left: 10px; padding: 4px 10px 4px 4px; }
    .creator-watermark-avatar { width: 20px; height: 20px; }
    .creator-watermark-name { font-size: 10px; max-width: 90px; }
    .creator-watermark-handle { font-size: 8px; max-width: 90px; }
  }
  @media (max-width: 400px) {
    .slide-content { padding: 20px 14px 18px; }
    .slide-1-content { padding: 18px 14px 48px; }
    .counter-dot { width: 5px; height: 5px; }
    .counter-dot.active { width: 12px; }
    .action-bar { gap: 10px; }
  }
"""


__all__ = ["_get_neon_responsive_css"]
