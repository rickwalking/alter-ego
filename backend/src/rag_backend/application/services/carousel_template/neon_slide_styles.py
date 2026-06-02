"""Neon Shell v2.0 slide-specific CSS (intro, content, summary, stat, insight, CTA)."""

from __future__ import annotations


def _get_neon_slide_css(theme: dict[str, str]) -> str:
    """Return slide component CSS matching the reference design."""
    primary = theme["primary"]
    accent = theme["accent"]
    return f"""
  .slide-content {{
    position: absolute;
    inset: 0;
    padding: 48px 36px 40px;
    display: flex;
    flex-direction: column;
    z-index: 2;
  }}

  .slide-1 {{ background: var(--bg); }}
  .slide-1 .slide-content {{ padding: 0; }}
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
    font-size: clamp(26px, 5.5vw, 34px);
    font-weight: 900;
    line-height: 1.08;
    letter-spacing: -0.02em;
    margin-bottom: 12px;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .s1-title .highlight {{ color: var(--accent); }}
  .s1-subtitle {{
    font-size: clamp(13px, 2.5vw, 15px);
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
    font-size: clamp(11px, 2.2vw, 13px);
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
    font-size: 11px;
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
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: var(--primary);
    margin-bottom: 10px;
    flex-shrink: 0;
  }}
  .slide-heading {{
    font-family: var(--font-heading);
    font-size: clamp(20px, 4.5vw, 28px);
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
    font-size: clamp(12px, 2.5vw, 15px);
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

  .feature-grid {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }}
  .feature-item {{
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 9px 12px;
    border-radius: 8px;
    background: rgba(255,255,255,0.015);
    border: 1px solid {primary}0F;
    min-width: 0;
    overflow: hidden;
  }}
  .feature-icon {{
    font-size: 16px;
    line-height: 1.5;
    flex-shrink: 0;
    width: 20px;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .feature-text {{ flex: 1; min-width: 0; }}
  .feature-title {{
    font-size: clamp(11px, 2.2vw, 13px);
    font-weight: 700;
    color: var(--text);
    margin-bottom: 1px;
    line-height: 1.3;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .feature-body {{
    font-size: clamp(10px, 2vw, 12px);
    color: var(--text-60);
    line-height: 1.5;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .feature-body strong {{ color: var(--text); font-weight: 600; }}

  .feature-grid.cols-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }}

  .stat-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin: 8px 0;
    flex-shrink: 0;
  }}
  .stat-card {{
    background: rgba(255,255,255,0.02);
    border: 1px solid {primary}14;
    border-radius: 8px;
    padding: 12px 6px;
    text-align: center;
    min-width: 0;
  }}
  .stat-number {{
    font-size: clamp(18px, 4vw, 24px);
    font-weight: 900;
    color: var(--accent);
    line-height: 1;
    margin-bottom: 3px;
    letter-spacing: -0.02em;
    overflow-wrap: break-word;
  }}
  .stat-label {{
    font-size: clamp(10px, 1.8vw, 11px);
    color: var(--text-60);
    line-height: 1.3;
    font-weight: 500;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .stat-detail {{
    font-size: clamp(8px, 1.5vw, 10px);
    color: var(--text-55);
    margin-top: 2px;
    font-family: var(--font-mono);
    overflow-wrap: break-word;
    word-break: break-word;
  }}

  .summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    flex: 1;
  }}
  .summary-grid .summary-item:nth-child(3) {{ grid-column: 1 / -1; }}
  .summary-item {{
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 14px 14px;
    border-radius: 8px;
    background: rgba(10,12,20,0.8);
    border: 1px solid {primary}26;
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    min-width: 0;
    overflow: hidden;
  }}
  .summary-item .summary-icon {{
    font-size: 20px;
    line-height: 1.3;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
  }}
  .summary-item .summary-text {{ flex: 1; min-width: 0; }}
  .summary-item .summary-title {{
    font-size: clamp(12px, 2.4vw, 14px);
    font-weight: 700;
    color: var(--text);
    margin-bottom: 2px;
    line-height: 1.3;
  }}
  .summary-item .summary-body {{
    font-size: clamp(10px, 2vw, 12px);
    color: var(--text-60);
    line-height: 1.5;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .summary-item .summary-body strong {{ color: var(--text); font-weight: 600; }}

  .insight-card {{
    padding: 12px 16px;
    border-radius: 6px;
    background: {accent}08;
    border: 1px solid {accent}14;
    font-size: clamp(11px, 2.2vw, 13px);
    font-style: italic;
    color: var(--text-60);
    line-height: 1.55;
    position: relative;
    flex-shrink: 0;
    margin-top: 4px;
    overflow-wrap: break-word;
    word-break: break-word;
  }}
  .insight-card::before {{
    content: '\\201C';
    position: absolute;
    top: -2px;
    left: 6px;
    font-size: 28px;
    font-weight: 900;
    color: var(--accent);
    opacity: 0.12;
    font-family: serif;
    line-height: 1;
  }}
  .insight-card strong {{
    color: var(--text);
    font-weight: 600;
    font-style: italic;
  }}
  .insight-attribution {{
    display: block;
    font-size: clamp(9px, 1.8vw, 11px);
    font-style: normal;
    color: var(--text-55);
    margin-top: 4px;
    font-family: var(--font-mono);
  }}

  .slide-cta {{
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
  .cta-icon {{ font-size: clamp(32px, 7vw, 40px); margin-bottom: 14px; flex-shrink: 0; }}
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
"""


__all__ = ["_get_neon_slide_css"]
