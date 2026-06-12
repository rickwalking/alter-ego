"""Neon Shell v2.0 structured component CSS (features, stats, summary, insight)."""

from __future__ import annotations


def get_neon_slide_component_css(theme: dict[str, str]) -> str:
    """Return CSS for feature grids, stat cards, summary grids and insight quotes."""
    primary = theme["primary"]
    accent = theme["accent"]
    return f"""  .feature-grid {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-height: 0;
    overflow: hidden;
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
  .feature-icon.numbered-step {{
    font-weight: 900;
    font-family: var(--font-mono);
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
    font-size: clamp(11px, 2.2vw, 13px);
    font-weight: 700;
    color: var(--text);
    margin-bottom: 1px;
    line-height: 1.3;
    overflow-wrap: break-word;
    word-break: break-word;
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

"""


__all__ = ["get_neon_slide_component_css"]
