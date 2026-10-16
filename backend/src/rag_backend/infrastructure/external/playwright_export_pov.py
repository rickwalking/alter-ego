"""Export-canvas overrides for the "Ponto de Vista" layouts (AE-0394).

The base POV CSS (``slide_styles_pov.py``) is sized for the ~420px app
preview. The exporter renders on a 1080x1350 (or 2160x2700) canvas and scales
the standard slide classes through its own injection; the POV classes were
never part of it, so POV slides exported with preview-sized type. These rules
are the POV counterpart, one set per export scale.
"""

from __future__ import annotations

_POV_EXPORT_RULES = """
  .pov-presentation {{
    padding: {pad_top}px {pad_x}px {pad_bottom}px !important;
    justify-content: center !important;
  }}
  .pov-copy {{
    max-width: 100% !important;
    max-height: none !important;
  }}
  .pov-presentation .slide-hero-number {{
    font-size: {counter}px !important;
  }}
  .pov-statement-heading {{
    font-size: {statement}px !important;
    line-height: 1.04 !important;
    letter-spacing: -0.02em !important;
    margin-top: {statement_gap}px !important;
    text-wrap: balance;
  }}
  .pov-statement-body {{
    font-size: {body}px !important;
    line-height: 1.42 !important;
    margin-top: {body_gap}px !important;
    max-width: 30ch;
    text-wrap: pretty;
  }}
  .pov-footer {{
    left: {pad_x}px !important;
    right: {pad_x}px !important;
    bottom: {footer_bottom}px !important;
    font-size: {footer}px !important;
  }}
  [data-layout="pov-hook"] {{
    justify-content: flex-start !important;
    padding-top: {hook_top}px !important;
  }}
  .pov-hook-heading {{
    font-size: {hook}px !important;
    line-height: 1.0 !important;
    letter-spacing: -0.025em !important;
    max-width: 92% !important;
    text-wrap: balance;
  }}
  .pov-hook-sub {{
    font-size: {hook_sub}px !important;
    line-height: 1.3 !important;
    max-width: 70% !important;
    margin-top: {hook_sub_gap}px !important;
  }}
  .pov-checklist {{
    gap: {check_gap}px !important;
    margin-top: {check_top}px !important;
  }}
  .pov-check-item {{
    font-size: {body}px !important;
    gap: {check_item_gap}px !important;
    line-height: 1.2 !important;
    align-items: center !important;
  }}
  .pov-check-icon {{
    flex: 0 0 {check_icon}px !important;
    height: {check_icon}px !important;
    border-radius: {check_radius}px !important;
  }}
  .pov-check-icon svg {{
    width: {check_svg}px !important;
    height: {check_svg}px !important;
  }}
  .pov-cta-sentence {{
    font-size: {cta}px !important;
    line-height: 1.14 !important;
    max-width: 22ch !important;
    margin: 0 auto {cta_gap}px !important;
    text-wrap: balance;
  }}
  .pov-cta-website {{
    font-size: {cta_site}px !important;
  }}
  .pov-quote-card {{
    padding: {quote_pad}px !important;
    margin-top: {quote_gap}px !important;
  }}
  .pov-quote-card .quote-text {{
    font-size: {quote}px !important;
    line-height: 1.35 !important;
  }}
  .quote-attribution {{
    gap: {quote_attr_gap}px !important;
    margin-top: {quote_attr_gap}px !important;
  }}
  .quote-avatar {{
    flex-basis: {quote_avatar}px !important;
    width: {quote_avatar}px !important;
    height: {quote_avatar}px !important;
    font-size: {quote_avatar_font}px !important;
  }}
  .quote-name, .quote-handle {{
    font-size: {quote_attr}px !important;
  }}
"""

# Pixel values for the 1080x1350 canvas; the HD canvas doubles every one.
_BASE_PX: dict[str, int] = {
    "pad_top": 88,
    "pad_x": 80,
    "pad_bottom": 150,
    "counter": 26,
    "statement": 84,
    "statement_gap": 22,
    "body": 36,
    "body_gap": 36,
    "footer_bottom": 56,
    "footer": 22,
    "hook_top": 92,
    "hook": 92,
    "hook_sub": 34,
    "hook_sub_gap": 24,
    "check_gap": 30,
    "check_top": 52,
    "check_item_gap": 24,
    "check_icon": 52,
    "check_radius": 12,
    "check_svg": 32,
    "cta": 44,
    "cta_gap": 28,
    "cta_site": 20,
    # AE-0406: the pov_news quote card.
    "quote": 38,
    "quote_pad": 32,
    "quote_gap": 36,
    "quote_attr_gap": 18,
    "quote_avatar": 60,
    "quote_avatar_font": 28,
    "quote_attr": 26,
}
_HD_FACTOR = 2

_INJECTION_TEMPLATE = (
    "const s = document.createElement('style');"
    "s.id = 'playwright-export-pov';"
    "s.textContent = {css};"
    "document.head.appendChild(s);"
)


def pov_export_css(*, hd: bool) -> str:
    """The POV export rules for the standard or the HD canvas."""
    factor = _HD_FACTOR if hd else 1
    values = {name: px * factor for name, px in _BASE_PX.items()}
    return _POV_EXPORT_RULES.format(**values)


def pov_export_injection(*, hd: bool) -> str:
    """JavaScript that appends the POV export rules to the page."""
    css = pov_export_css(hd=hd)
    escaped = css.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    return _INJECTION_TEMPLATE.format(css=f"`{escaped}`")


__all__ = ["pov_export_css", "pov_export_injection"]
