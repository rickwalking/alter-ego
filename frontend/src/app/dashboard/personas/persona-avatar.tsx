import {
  PERSONA_COLORS,
  dimPersonaColor,
  type PersonaAccent,
} from "@/app/dashboard/personas/constants";

export interface PersonaAvatarProps {
  initials: string;
  accent: PersonaAccent;
}

export function PersonaAvatar({
  initials,
  accent,
}: PersonaAvatarProps): React.ReactElement {
  const color = PERSONA_COLORS[accent];
  return (
    <div
      style={{
        width: 48,
        height: 48,
        borderRadius: 12,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
        fontSize: 20,
        fontWeight: 700,
        flexShrink: 0,
        background: dimPersonaColor(color),
        color,
      }}
    >
      {initials}
    </div>
  );
}
