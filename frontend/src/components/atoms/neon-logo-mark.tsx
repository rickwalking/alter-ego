import { NEON_CYAN } from "@/constants/neon";

interface NeonLogoMarkProps {
  boxShadow: string;
  decorative?: boolean;
}

export function NeonLogoMark({
  boxShadow,
  decorative = false,
}: Readonly<NeonLogoMarkProps>): React.ReactElement {
  return (
    <span
      style={{
        width: "32px",
        height: "32px",
        border: `2px solid ${NEON_CYAN}`,
        borderRadius: "4px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: "14px",
        fontWeight: 700,
        color: NEON_CYAN,
        boxShadow,
      }}
      aria-hidden={decorative ? "true" : undefined}
    >
      P
    </span>
  );
}
