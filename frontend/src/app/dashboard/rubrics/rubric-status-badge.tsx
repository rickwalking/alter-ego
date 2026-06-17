import { RUBRIC_COLORS } from "@/modules/editorial-operations";
import { dimColor } from "@/app/dashboard/rubrics/helpers";
import { StatusPill } from "@/components/atoms/status-pill";

interface RubricStatusBadgeProps {
  status: "active" | "inactive";
}

export function RubricStatusBadge({
  status,
}: RubricStatusBadgeProps): React.ReactElement {
  const isActive = status === "active";
  const color = isActive ? RUBRIC_COLORS.teal : RUBRIC_COLORS.amber;

  return (
    <StatusPill label={status} color={color} background={dimColor(color)} />
  );
}
