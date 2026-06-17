import { NEON_CYAN } from "@/constants/neon";

/**
 * The shared "eyebrow" label that sits above each marketing section heading:
 * a short neon rule followed by an uppercase mono label. Identical markup is
 * used by the Features, Latest Posts, and About sections.
 */
export function MarketingSectionEyebrow({
  label,
}: {
  label: string;
}): React.ReactElement {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: "11px",
        fontWeight: 700,
        textTransform: "uppercase",
        letterSpacing: "3px",
        color: NEON_CYAN,
        marginBottom: "12px",
      }}
    >
      <span
        style={{
          width: "24px",
          height: "1px",
          background: NEON_CYAN,
          boxShadow: `0 0 8px ${NEON_CYAN}`,
        }}
      />
      {label}
    </div>
  );
}
