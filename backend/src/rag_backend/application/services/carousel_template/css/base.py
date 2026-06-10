"""Neon Shell v2.0 base CSS (reset, layout, grid, watermark, action bar, caption)."""

from __future__ import annotations


def _get_neon_base_css(theme: dict[str, str]) -> str:
    """Return base layout and structural CSS matching the reference design."""
    primary = theme["primary"]
    accent = theme["accent"]
    bg = theme["background"]
    return f"""
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    background: #060a12;
    color: rgba(255,255,255,0.85);
    line-height: 1.6;
    overflow-x: hidden;
    -webkit-font-smoothing: antialiased;
  }}

  @media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }}
  }}

  :root {{
    --primary: {primary};
    --primary-dim: {primary}26;
    --primary-glow: {primary}14;
    --accent: {accent};
    --accent-dim: {accent}1F;
    --bg: {bg};
    --text: #ffffff;
    --text-60: rgba(255,255,255,0.63);
    --text-48: rgba(255,255,255,0.48);
    --text-55: rgba(255,255,255,0.55);
    --text-06: rgba(255,255,255,0.06);
    --font-mono: 'JetBrains Mono', ui-monospace, monospace;
    --font-heading: 'Inter', system-ui, -apple-system, sans-serif;
  }}

  body::after {{
    content: '';
    position: fixed;
    inset: 0;
    z-index: 9999;
    pointer-events: none;
    background: repeating-linear-gradient(
      0deg, transparent, transparent 2px,
      {primary}08 2px, {primary}08 4px
    );
  }}

  .grid-bg {{
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    perspective: 600px;
    overflow: hidden;
  }}
  .grid-bg-inner {{
    position: absolute;
    inset: -50% -50%;
    width: 200%; height: 200%;
    background-image:
      linear-gradient({primary}08 1px, transparent 1px),
      linear-gradient(90deg, {primary}08 1px, transparent 1px);
    background-size: 60px 60px;
    transform: rotateX(60deg);
    animation: grid-drift 25s linear infinite;
  }}
  @keyframes grid-drift {{
    0% {{ transform: rotateX(60deg) translateY(0); }}
    100% {{ transform: rotateX(60deg) translateY(60px); }}
  }}

  .page-header {{
    position: relative;
    z-index: 10;
    text-align: center;
    padding: 40px 20px 20px;
  }}
  .page-header h1 {{
    font-size: clamp(16px, 3vw, 20px);
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.02em;
    overflow-wrap: break-word;
  }}
  .page-header .sub {{
    font-size: clamp(11px, 2vw, 13px);
    color: var(--text-48);
    margin-top: 4px;
    font-family: var(--font-mono);
  }}

  .feed {{
    position: relative;
    z-index: 1;
    max-width: 600px;
    margin: 0 auto;
    padding: 0 16px 60px;
  }}

  .ig-post {{ margin-bottom: 24px; }}

  .ig-slide {{
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid {primary}14;
    position: relative;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5);
  }}
  .ig-slide-inner {{
    position: relative;
    width: 100%;
    aspect-ratio: 1080 / 1350;
    overflow: hidden;
  }}

  .bg-glow {{
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
  }}
  .bg-glow::before {{
    content: '';
    position: absolute;
    width: min(450px, 70vw);
    height: min(450px, 70vw);
    border-radius: 50%;
    top: -80px;
    right: -120px;
    background: radial-gradient(circle, {primary}0F 0%, transparent 70%);
  }}
  .bg-glow::after {{
    content: '';
    position: absolute;
    width: min(350px, 55vw);
    height: min(350px, 55vw);
    border-radius: 50%;
    bottom: -60px;
    left: -80px;
    background: radial-gradient(circle, {accent}0A 0%, transparent 70%);
  }}

  .creator-watermark {{
    position: absolute;
    bottom: 16px;
    left: 16px;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 16px 8px 8px;
    background: rgba(6,10,18,0.82);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid {primary}26;
    border-radius: 100px;
    max-width: calc(100% - 32px);
  }}
  .creator-watermark-avatar {{
    width: 44px;
    height: 44px;
    border-radius: 50%;
    overflow: hidden;
    flex-shrink: 0;
    border: 2px solid var(--primary);
    box-shadow: 0 0 14px var(--primary-dim);
  }}
  .creator-watermark-avatar img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}
  .creator-watermark-text {{
    display: flex;
    flex-direction: column;
    min-width: 0;
  }}
  .creator-watermark-name {{
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 180px;
  }}
  .creator-watermark-handle {{
    font-size: 12px;
    color: var(--text-60);
    font-family: var(--font-mono);
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 180px;
  }}

  .slide-counter {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
  }}
  .counter-dots {{
    display: flex;
    gap: 5px;
    min-width: 0;
  }}
  .counter-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(255,255,255,0.18);
    transition: background 0.3s, width 0.3s, border-radius 0.3s, box-shadow 0.3s;
    flex-shrink: 0;
  }}
  .counter-dot.active {{
    background: var(--primary);
    box-shadow: 0 0 10px var(--primary-dim);
    width: 24px;
    border-radius: 4px;
  }}
  .counter-dot.past {{ background: {primary}40; }}
  .counter-label {{
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--text-55);
    flex-shrink: 0;
    overflow-wrap: break-word;
    word-break: break-word;
  }}

  .action-bar {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 0;
  }}
  .action-btn {{
    display: flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: none;
    color: var(--text-60);
    font-size: 13px;
    cursor: pointer;
    padding: 4px;
    transition: color 0.2s;
  }}
  .action-btn:hover {{ color: var(--primary); }}
  .action-btn svg {{ width: 20px; height: 20px; display: block; flex-shrink: 0; }}
  .action-save {{ margin-left: auto; }}

  .caption {{
    padding: 6px 0 16px;
    font-size: clamp(12px, 2.2vw, 13px);
    color: var(--text-60);
    line-height: 1.6;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .caption strong {{ color: var(--text); font-weight: 600; }}
  .caption a {{ color: var(--primary); text-decoration: none; }}
  .caption a:hover {{ text-decoration: underline; }}
  .caption-hashtags {{
    color: var(--primary);
    margin-top: 4px;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
"""


__all__ = ["_get_neon_base_css"]
