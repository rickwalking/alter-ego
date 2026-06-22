"""Carousel theme palettes and brand palettes.

Keyword maps for auto-detection live in ``carousel_theme_keywords``.
"""

# Theme color palettes
CAROUSEL_THEMES: dict[str, dict[str, str]] = {
    "cybersecurity": {
        "primary": "#ef4444",
        "accent": "#00d4ff",
        "background": "#0a0e17",
    },
    "ai_competition": {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
    "developer_skills": {
        "primary": "#0ac5a8",
        "accent": "#8b5cf6",
        "background": "#080c12",
    },
    "source_code": {
        "primary": "#a855f7",
        "accent": "#f97316",
        "background": "#0c0a14",
    },
    "social_engineering": {
        "primary": "#f59e0b",
        "accent": "#ef4444",
        "background": "#0a0c14",
    },
    # Dark variants (drop-in for the neon/neo-anime image presets). Same
    # dark-background + saturated-accent shape as the category themes above,
    # so they render correctly through the existing dark strategies.
    "plasma_magenta": {
        "primary": "#ec4899",
        "accent": "#22d3ee",
        "background": "#0a0a14",
    },
    "acid_lime": {
        "primary": "#a3e635",
        "accent": "#06b6d4",
        "background": "#0b0f0a",
    },
    "mono_indigo": {
        "primary": "#6366f1",
        "accent": "#e5e7eb",
        "background": "#0b0b14",
    },
    "ember_crimson": {
        "primary": "#f43f5e",
        "accent": "#fb923c",
        "background": "#140a0c",
    },
    "blueprint": {
        "primary": "#38bdf8",
        "accent": "#f8fafc",
        "background": "#0a192f",
    },
    # Light / editorial palettes. These have LIGHT backgrounds and must be
    # paired with the flat-editorial image strategy; rendering them through a
    # dark "neon glow" strategy contradicts the prompt. They are explicit-
    # select only and are deliberately excluded from AUTO rotation
    # (see ``AUTO_ROTATION_THEME_KEYS``).
    "risograph": {
        "primary": "#ff5c39",
        "accent": "#1d4ed8",
        "background": "#fbf7f0",
    },
    "paper_editorial": {
        "primary": "#111827",
        "accent": "#2563eb",
        "background": "#f7f5f0",
    },
    "clinical_mint": {
        "primary": "#0f172a",
        "accent": "#0d9488",
        "background": "#f0fdfa",
    },
}

# Keys eligible for AUTO theme rotation. Deliberately limited to the original
# dark category themes so the AUTO resolver never hands a LIGHT palette to the
# dark neon/neo-anime image strategies. New explicit-select palettes
# (dark variants + light/editorial) are intentionally absent here.
AUTO_ROTATION_THEME_KEYS: tuple[str, ...] = (
    "cybersecurity",
    "ai_competition",
    "developer_skills",
    "source_code",
    "social_engineering",
)

# Keys whose palette uses a LIGHT background and therefore requires the
# flat-editorial image strategy rather than a dark neon strategy.
LIGHT_THEME_KEYS: frozenset[str] = frozenset({
    "risograph",
    "paper_editorial",
    "clinical_mint",
})

# Brand color palettes
BRAND_PALETTES: dict[str, dict[str, str]] = {
    "anthropic": {
        "primary": "#ea580c",
        "accent": "#22d3ee",
        "background": "#0a0b12",
    },
    "google": {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
    "openai": {
        "primary": "#10a37f",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
    "meta": {
        "primary": "#8b5cf6",
        "accent": "#0ac5a8",
        "background": "#0c0a14",
    },
    "microsoft": {
        "primary": "#0078d4",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
    "glm": {
        "primary": "#2563eb",
        "accent": "#06b6d4",
        "background": "#0a0e17",
    },
}


__all__ = [
    "AUTO_ROTATION_THEME_KEYS",
    "BRAND_PALETTES",
    "CAROUSEL_THEMES",
    "LIGHT_THEME_KEYS",
]
