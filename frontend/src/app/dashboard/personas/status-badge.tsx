import {
  PERSONA_COLORS,
  dimPersonaColor,
} from "@/app/dashboard/personas/constants";
import { StatusPill } from "@/components/atoms/status-pill";

export interface StatusBadgeProps {
  status: "active" | "inactive";
}

export function StatusBadge({ status }: StatusBadgeProps): React.ReactElement {
  const isActive = status === "active";
  const color = isActive ? PERSONA_COLORS.teal : PERSONA_COLORS.amber;
  return (
    <StatusPill
      label={status}
      color={color}
      background={dimPersonaColor(color)}
    />
  );
}
