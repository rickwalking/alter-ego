import { dimColor, getRubricColor } from "@/app/dashboard/rubrics/helpers";
import type { RubricColorKey } from "@/features/dashboard/rubrics/types";

interface RubricBadgeProps {
  label: string;
  color: RubricColorKey;
}

export function RubricBadge({ label, color }: RubricBadgeProps): React.ReactElement {
  const c = getRubricColor(color);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        color: c,
        background: dimColor(c),
      }}
    >
      {label}
    </span>
  );
}
