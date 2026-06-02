import {
  PERSONA_COLORS,
  dimPersonaColor,
} from "@/app/dashboard/personas/constants";

export interface StatusBadgeProps {
  status: "active" | "inactive";
}

export function StatusBadge({ status }: StatusBadgeProps): React.ReactElement {
  const isActive = status === "active";
  const color = isActive ? PERSONA_COLORS.teal : PERSONA_COLORS.amber;
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
        background: dimPersonaColor(color),
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
