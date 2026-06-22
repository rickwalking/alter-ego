"""Neon Shell v2.0 CTA, hero-bg and closing slide CSS."""

from __future__ import annotations


def get_neon_slide_closing_css(theme: dict[str, str]) -> str:
    """Return CSS for CTA, hero-background and closing slides."""
    primary = theme["primary"]
    return f"""  .slide-cta {{
    background: var(--bg);
    text-align: center;
  }}
  .slide-cta.slide-content {{
    align-items: center;
    justify-content: center;
  }}
  .slide-cta .slide-number {{
    text-align: center;
    width: 100%;
  }}
  .slide-cta .cta-title {{
    text-align: center;
    margin-inline: auto;
  }}
  .slide-cta .cta-body {{
    text-align: center;
    margin-inline: auto;
  }}
  .cta-icon {{ font-size: clamp(32px, 7vw, 40px);
    margin-bottom: 14px; flex-shrink: 0; }}
  .cta-title {{
    font-family: var(--font-heading);
    font-size: clamp(20px, 4.5vw, 26px);
    font-weight: 900;
    letter-spacing: -0.02em;
    margin-bottom: 10px;
    line-height: 1.2;
    max-width: 440px;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .cta-title .highlight {{ color: var(--accent); }}
  .cta-body {{
    font-size: clamp(12px, 2.4vw, 14px);
    color: var(--text-60);
    line-height: 1.6;
    margin-bottom: 22px;
    max-width: 440px;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .cta-row {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: center;
  }}
  .cta-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 20px;
    border-radius: 6px;
    font-size: clamp(12px, 2.2vw, 13px);
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
    transition: background 0.2s, transform 0.2s, box-shadow 0.2s;
    border: none;
    white-space: nowrap;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .cta-btn.primary {{
    background: linear-gradient(135deg, var(--primary) 0%, #c2410c 100%);
    color: #fff;
    box-shadow: 0 0 16px var(--primary-dim);
  }}
  .cta-btn.primary:hover {{
    transform: translateY(-1px);
    box-shadow: 0 0 24px var(--primary-dim);
  }}
  .cta-btn.secondary {{
    background: transparent;
    color: var(--primary);
    border: 1px solid {primary}40;
  }}
  .cta-btn.secondary:hover {{
    background: var(--primary-dim);
    border-color: var(--primary);
    transform: translateY(-1px);
  }}

  /* ── Hero-bg layout (background image + gradient + bottom text) ── */
  .slide-hero-bg-img {{
    position: absolute;
    inset: 0;
    z-index: 0;
    overflow: hidden;
  }}
  .slide-hero-bg-img img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 25%;
    display: block;
  }}
  .slide-hero-bg-gradient {{
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: linear-gradient(
      180deg,
      var(--scrim-0) 0%,
      var(--scrim-25) 25%,
      var(--scrim-50) 50%,
      var(--bg) 70%
    );
  }}
  .slide-hero-content {{
    position: absolute;
    inset: 0;
    z-index: 3;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 40px 36px 96px;
  }}
  .slide-hero-content.is-centered {{
    justify-content: center;
    align-items: center;
    text-align: center;
  }}
  .slide-hero-main {{
    display: flex;
    flex-direction: column;
    max-height: calc(100% - 112px);
  }}
  .slide-hero-content .creator-watermark {{
    position: absolute;
    bottom: 22px;
    left: 40px;
    z-index: 10;
  }}
  .slide-hero-content.is-centered .creator-watermark {{
    left: auto;
  }}

  .slide-hero-content .s1-swipe,
  .slide-presentation .s1-swipe {{
    position: absolute;
    bottom: 22px;
    right: 40px;
    z-index: 10;
  }}
  .slide-presentation .creator-watermark {{
    position: absolute;
    bottom: 22px;
    left: 40px;
    z-index: 10;
  }}
  .slide-hero-number {{
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: var(--primary);
    margin-bottom: 8px;
  }}
  .slide-hero-heading {{
    font-family: var(--font-heading);
    font-size: clamp(29px, 5.8vw, 38px);
    font-weight: 900;
    line-height: 1.08;
    letter-spacing: -0.02em;
    margin-bottom: 10px;
  }}
  .slide-hero-heading .highlight {{ color: var(--accent); }}
  .slide-hero-heading strong {{ color: var(--accent); }}
  .slide-hero-body {{
    font-size: clamp(14px, 2.45vw, 16px);
    color: var(--text-60);
    line-height: 1.52;
  }}
  .slide-hero-body strong {{ color: var(--accent); font-weight: 700; }}

  /* ── Closing slide (centered) ── */
  .slide-closing {{
    text-align: center;
    align-items: center;
    justify-content: center;
  }}
  .slide-closing.slide-content {{
    padding: 48px 48px 40px;
  }}
  .closing-card {{
    display: flex;
    flex-direction: column;
    align-items: center;
    width: min(100%, 460px);
    padding: 28px 30px 32px;
    border-radius: 18px;
    background:
      linear-gradient(180deg, var(--card-bg-1), var(--card-bg-2)),
      radial-gradient(circle at 50% 0%, {primary}1F, transparent 58%);
    border: 1px solid {primary}33;
    box-shadow: 0 0 36px var(--primary-glow), inset 0 0 32px rgba(255,255,255,0.025);
  }}
  .closing-avatar {{
    width: 112px;
    height: 112px;
    border-radius: 50%;
    overflow: hidden;
    margin-bottom: 18px;
    border: 3px solid var(--primary);
    box-shadow: 0 0 28px var(--primary-dim);
  }}
  .closing-avatar img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}
  .closing-name {{
    font-family: var(--font-heading);
    font-size: clamp(30px, 6vw, 44px);
    font-weight: 900;
    line-height: 1.05;
    color: var(--text);
    margin-bottom: 6px;
  }}
  .closing-handle {{
    font-family: var(--font-mono);
    font-size: clamp(16px, 2.8vw, 20px);
    color: var(--text-60);
    margin-bottom: 18px;
  }}
  .closing-website {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 11px 24px;
    border-radius: 6px;
    background: linear-gradient(135deg, var(--primary) 0%, #7c3aed 100%);
    color: #fff;
    font-family: var(--font-heading);
    font-size: clamp(16px, 2.6vw, 20px);
    font-weight: 700;
    text-decoration: none;
    margin-bottom: 18px;
    box-shadow: 0 0 20px var(--primary-dim);
  }}
  .closing-cta {{
    font-family: var(--font-mono);
    font-size: clamp(13px, 2vw, 16px);
    color: var(--text-55);
    letter-spacing: 1px;
  }}
"""


__all__ = ["get_neon_slide_closing_css"]
