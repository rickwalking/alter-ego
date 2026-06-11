"""Neon Shell v2.0 base slide shell CSS
(artwork, overlay, intro, content, hero image).
"""

from __future__ import annotations


def get_neon_slide_shell_css(theme: dict[str, str]) -> str:
    """Return base shell CSS for artwork, overlay, intro and content slides."""
    primary = theme["primary"]
    return f"""
  .slide-artwork {{
    position: absolute;
    inset: 0;
    z-index: 0;
    overflow: hidden;
  }}
  .slide-artwork img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 25%;
    display: block;
  }}
  .slide-overlay {{
    position: absolute;
    inset: 0;
    z-index: 1;
    background:
      linear-gradient(
        180deg,
        rgba(10,12,20,0.08) 0%,
        rgba(10,12,20,0.35) 25%,
        rgba(10,12,20,0.75) 50%,
        var(--bg) 70%
      );
    pointer-events: none;
  }}
  .slide-presentation {{
    position: absolute;
    inset: 0;
    z-index: 2;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 40px 36px 96px;
    pointer-events: none;
  }}
  .slide-presentation-copy {{
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    flex: 0 0 auto;
    margin-top: auto;
    min-height: 0;
    max-height: calc(100% - 112px);
    overflow: hidden;
    pointer-events: auto;
  }}

  .slide-content {{
    position: absolute;
    inset: 0;
    padding: 48px 36px 40px;
    display: flex;
    flex-direction: column;
    z-index: 2;
  }}

  .slide-1-bg-img {{
    position: absolute;
    inset: 0;
    z-index: 0;
    overflow: hidden;
  }}
  .slide-1-bg-img img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 25%;
    display: block;
  }}
  .slide-1-bg-gradient {{
    position: absolute;
    inset: 0;
    z-index: 1;
    background:
      linear-gradient(
        180deg,
        rgba(10,12,20,0.08) 0%,
        rgba(10,12,20,0.35) 25%,
        rgba(10,12,20,0.75) 50%,
        var(--bg) 70%
      );
    pointer-events: none;
  }}
  .slide-1-content {{
    position: absolute;
    inset: 0;
    z-index: 3;
    display: flex;
    flex-direction: column;
    padding: 40px 36px 64px;
  }}
  .slide-1-main {{
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
  }}
  .s1-badge {{
    display: inline-flex;
    align-self: flex-start;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    color: var(--primary);
    background: var(--primary-dim);
    border: 1px solid {primary}33;
    margin-bottom: 16px;
  }}
  .s1-badge-dot {{
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--primary);
    box-shadow: 0 0 6px var(--primary-dim);
    animation: pulse-dot 2s ease-in-out infinite;
    flex-shrink: 0;
  }}
  @keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
  }}
  .s1-title {{
    font-family: var(--font-heading);
    font-size: clamp(29px, 5.8vw, 38px);
    font-weight: 900;
    line-height: 1.08;
    letter-spacing: -0.02em;
    margin-bottom: 12px;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .s1-title .highlight {{ color: var(--accent); }}
  .s1-subtitle {{
    font-size: clamp(14px, 2.7vw, 17px);
    color: var(--text-60);
    line-height: 1.6;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .s1-subtitle strong {{ color: var(--text); font-weight: 600; }}
  .s1-tldr {{
    margin-top: 12px;
    padding: 10px 14px;
    border-radius: 6px;
    background: var(--primary-dim);
    border: 1px solid {primary}26;
    font-size: clamp(12px, 2.3vw, 14px);
    font-weight: 500;
    color: var(--text-60);
    line-height: 1.5;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .s1-tldr strong {{ color: var(--text); font-weight: 700; }}
  .s1-footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid var(--text-06);
  }}
  .s1-niche {{
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-55);
    letter-spacing: 2px;
    text-transform: uppercase;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .s1-swipe {{
    font-size: 14px;
    font-weight: 600;
    color: var(--primary);
    font-family: var(--font-mono);
    letter-spacing: 1px;
    flex-shrink: 0;
    animation: swipe-pulse 2s ease-in-out infinite;
  }}
  @keyframes swipe-pulse {{
    0%, 100% {{ opacity: 0.6; transform: translateX(0); }}
    50% {{ opacity: 1; transform: translateX(3px); }}
  }}

  .content-slide {{ background: var(--bg); }}
  .slide-number {{
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: var(--primary);
    margin-bottom: 10px;
    flex-shrink: 0;
  }}
  .slide-heading {{
    font-family: var(--font-heading);
    font-size: clamp(23px, 4.8vw, 32px);
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -0.02em;
    margin-bottom: 14px;
    flex-shrink: 0;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .slide-heading .highlight {{ color: var(--accent); }}
  .slide-body {{
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }}

  .body-p {{
    font-size: clamp(13px, 2.7vw, 17px);
    font-weight: 400;
    color: var(--text-60);
    line-height: 1.55;
    margin-bottom: 12px;
    flex-shrink: 0;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .body-p strong {{ color: var(--text); font-weight: 700; }}
  .code-tag {{
    display: inline-block;
    padding: 1px 7px;
    margin: 0 1px;
    border-radius: 4px;
    background: var(--primary-dim);
    color: var(--primary);
    font-family: var(--font-mono);
    font-size: 0.82em;
    font-weight: 600;
    letter-spacing: 0.3px;
    border: 1px solid {primary}1F;
    line-height: 1.4;
  }}

  .hero-img {{
    width: 100%;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid {primary}1A;
    flex-shrink: 0;
    margin-bottom: 10px;
    position: relative;
  }}
  .hero-img-sm {{ height: 110px; }}
  .hero-img-md {{ height: 130px; }}
  .hero-img-lg {{ height: 150px; }}
  .hero-img img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}
  .hero-img::after {{
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, {primary}0A 0%, transparent 50%);
    pointer-events: none;
  }}

"""


__all__ = ["get_neon_slide_shell_css"]
