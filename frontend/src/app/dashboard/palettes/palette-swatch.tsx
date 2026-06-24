interface PaletteSwatchProps {
  primary: string;
  accent: string;
  background: string;
  /** Accessible description, e.g. the palette name. */
  label: string;
  height?: number;
}

const SWATCH_PARTS = ["primary", "accent", "background"] as const;

/**
 * The three-colour identity band for a palette — the colours ARE the content,
 * so they get the visual weight rather than a generic icon card. Background sits
 * last and widest so the card reads like a real slide surface.
 */
export function PaletteSwatch({
  primary,
  accent,
  background,
  label,
  height = 72,
}: PaletteSwatchProps): React.ReactElement {
  const colours: Record<(typeof SWATCH_PARTS)[number], string> = {
    primary,
    accent,
    background,
  };
  return (
    <div
      className="flex overflow-hidden rounded-lg border border-white/10"
      style={{ height }}
      role="img"
      aria-label={`${label}: primary ${primary}, accent ${accent}, background ${background}`}
    >
      {SWATCH_PARTS.map((part) => (
        <div
          key={part}
          aria-hidden="true"
          style={{
            backgroundColor: colours[part],
            flex: part === "background" ? 2 : 1,
          }}
        />
      ))}
    </div>
  );
}
