import { getScoreClass } from "@/app/dashboard/rubrics/helpers";
import type { ScoreLevel } from "@/app/dashboard/rubrics/helpers";

interface ScoreCellProps {
  label: string;
  level: ScoreLevel;
}

export function ScoreCell({
  label,
  level,
}: ScoreCellProps): React.ReactElement {
  const { bg, color } = getScoreClass(level);
  return (
    <span
      style={{
        textAlign: "center",
        fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
        fontSize: 12,
        fontWeight: 700,
        padding: "4px 8px",
        borderRadius: 4,
        background: bg,
        color,
      }}
    >
      {label}
    </span>
  );
}
