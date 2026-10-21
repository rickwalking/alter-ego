"""CSS for the "Ponto de Vista" layouts (growth plan 16.3 B/D).

Solid palette backgrounds with a subtle texture instead of generated art,
large left-aligned type, one accent colour, the owner's cut-out photo on
slide 1 and a follow-focused CTA card.
"""

from __future__ import annotations


def get_pov_slide_css(_theme: dict[str, str]) -> str:
    """Return the POV layout CSS (uses the shell's colour variables)."""
    return """
  .pov-solid {
    position: absolute;
    inset: 0;
    z-index: 0;
    background:
      radial-gradient(circle at 18% 12%, var(--primary-glow) 0%, transparent 45%),
      repeating-linear-gradient(135deg, var(--text-06) 0 1px, transparent 1px 14px),
      var(--bg);
  }
  .pov-presentation {
    justify-content: flex-start;
    padding: 40px 32px 64px;
  }
  .pov-copy {
    justify-content: flex-start;
    margin-top: 0;
    max-width: 92%;
  }
  .pov-statement-heading {
    font-family: var(--font-heading);
    font-size: clamp(27px, 5.6vw, 34px);
    line-height: 1.08;
    font-weight: 800;
    color: var(--text);
    margin: 12px 0 0;
  }
  .pov-statement-heading strong { color: var(--accent); }
  .pov-statement-body {
    font-size: clamp(14px, 2.9vw, 18px);
    line-height: 1.4;
    color: var(--text-60);
    margin: 14px 0 0;
  }
  .pov-footer {
    position: absolute;
    left: 32px;
    right: 32px;
    bottom: 22px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-48);
  }
  .pov-hook-heading {
    font-family: var(--font-heading);
    font-size: clamp(32px, 7vw, 44px);
    line-height: 1.02;
    font-weight: 900;
    color: var(--text);
    max-width: 62%;
    margin: 0;
  }
  .pov-hook-heading strong { color: var(--accent); }
  .pov-hook-sub {
    font-size: clamp(14px, 2.8vw, 17px);
    line-height: 1.3;
    color: var(--text-60);
    max-width: 58%;
    margin: 14px 0 0;
  }
  /* AE-0394: the owner's photo fills slide 1; a scrim fades its top into the
     background so the hook reads over it. A transparent cut-out still sits
     on the .pov-solid texture. */
  .pov-hook-photo {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    z-index: 1;
  }
  .pov-hook-photo img {
    width: 100%;
    height: 100%;
    max-width: none;
    max-height: none;
    object-fit: cover;
    object-position: center 40%;
    display: block;
  }
  .pov-hook-photo::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--bg) 92%, transparent) 0%,
      color-mix(in srgb, var(--bg) 55%, transparent) 26%,
      transparent 44%,
      transparent 78%,
      color-mix(in srgb, var(--bg) 55%, transparent) 100%
    );
  }
  [data-layout="pov-hook"] .pov-hook-heading { max-width: 92%; }
  [data-layout="pov-hook"] .pov-hook-sub {
    max-width: 70%;
    color: var(--text-80, var(--text));
  }
  .pov-checklist {
    list-style: none;
    padding: 0;
    margin: 18px 0 0;
    display: flex;
    flex-direction: column;
    gap: 11px;
  }
  .pov-check-item {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    font-size: clamp(14px, 2.9vw, 18px);
    line-height: 1.25;
    color: var(--text);
  }
  .pov-check-icon {
    flex: 0 0 22px;
    height: 22px;
    border-radius: 5px;
    background: var(--accent);
    color: var(--bg);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .pov-check-icon svg { width: 14px; height: 14px; }
  .pov-cta { z-index: 2; justify-content: center; }
  .pov-cta-card { gap: 8px; }
  .pov-cta-sentence {
    font-family: var(--font-heading);
    font-size: clamp(20px, 4.4vw, 27px);
    line-height: 1.15;
    font-weight: 800;
    color: var(--text);
    text-align: center;
    margin: 0 0 12px;
  }
  .pov-cta-website {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-48);
  }
  /* AE-0406: the pov_news quote card (verbatim quote + attribution row). */
  .pov-quote-card { margin: 16px 0 0; font-style: normal; }
  .pov-quote-card .quote-text {
    margin: 0;
    font-style: italic;
    color: var(--text);
    font-size: clamp(13px, 2.7vw, 16px);
    line-height: 1.4;
  }
  .quote-attribution {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    font-style: normal;
  }
  .quote-avatar {
    flex: 0 0 26px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--accent);
    color: var(--bg);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 13px;
  }
  .quote-name { color: var(--text); font-weight: 700; font-size: 12px; }
  .quote-handle {
    color: var(--text-55, var(--text));
    font-family: var(--font-mono);
    font-size: 11px;
  }
"""


__all__ = ["get_pov_slide_css"]
