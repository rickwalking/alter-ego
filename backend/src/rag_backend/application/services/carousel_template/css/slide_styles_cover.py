"""CSS for the GrokBot screenshot cover on slide 1 (AE-0418, ADR-0024).

The screenshot sits as a centred card on the solid ``.pov-solid`` background:
rounded corners, a soft shadow, aspect kept (never cropped), the title above
and a small mono credit under it.
"""

from __future__ import annotations


def get_cover_slide_css(_theme: dict[str, str]) -> str:
    """Return the cover-card CSS (uses the shell's colour variables)."""
    return """
  .cover-card-heading {
    font-family: var(--font-heading);
    font-size: clamp(26px, 5.4vw, 34px);
    line-height: 1.08;
    font-weight: 800;
    color: var(--text);
    margin: 0;
  }
  .cover-card-heading strong { color: var(--accent); }
  .cover-card-frame {
    position: absolute;
    left: 8%;
    right: 8%;
    top: 34%;
    bottom: 12%;
    z-index: 1;
    margin: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
  }
  .cover-card-frame img {
    max-width: 100%;
    max-height: calc(100% - 28px);
    object-fit: contain;
    border-radius: 18px;
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55), 0 0 0 1px var(--text-06);
    display: block;
  }
  .cover-card-credit {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-60);
    letter-spacing: 0.02em;
  }
"""


__all__ = ["get_cover_slide_css"]
