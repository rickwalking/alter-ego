import { NEON_CYAN, NEON_CYAN_DIM } from "@/constants/neon";

const CYAN = NEON_CYAN;
const CYAN_DIM = NEON_CYAN_DIM;

export interface SectionNumberProps {
  num: number;
}

export function SectionNumber({ num }: SectionNumberProps): React.ReactElement {
  return (
    <span
      style={{
        width: "22px",
        height: "22px",
        borderRadius: "50%",
        background: CYAN_DIM,
        color: CYAN,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: "11px",
        fontWeight: 700,
      }}
    >
      {num}
    </span>
  );
}
