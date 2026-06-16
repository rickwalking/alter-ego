import { RUBRIC_COLORS } from "@/modules/editorial-operations";
import { dimColor } from "@/app/dashboard/rubrics/helpers";

interface RubricStatusBadgeProps {
  status: "active" | "inactive";
}

export function RubricStatusBadge({
  status,
}: RubricStatusBadgeProps): React.ReactElement {
  const isActive = status === "active";
  const color = isActive ? RUBRIC_COLORS.teal : RUBRIC_COLORS.amber;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 10px",
        borderRadius: 20,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        color,
        background: dimColor(color),
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
        }}
      />
      {status}
    </span>
  );
}
