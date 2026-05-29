import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import {
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_PERSONA_AVATAR_BORDER,
  TEXT,
  TEXT_MUTED,
} from "@/constants/neon";

export interface NeonPersonaCardProps {
  name: string;
  role: string;
  description: string;
  skills: string[];
  avatarUrl?: string;
}

export function NeonPersonaCard({
  name,
  role,
  description,
  skills,
  avatarUrl,
}: NeonPersonaCardProps): React.ReactElement {
  return (
    <NeonCard hover padding="md">
      <div className="flex items-start gap-4 mb-3">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold shrink-0"
          style={{
            background: NEON_CYAN_DIM,
            color: NEON_CYAN,
            border: `1px solid ${NEON_PERSONA_AVATAR_BORDER}`,
          }}
        >
          {avatarUrl ? (
            <img src={avatarUrl} alt="" className="w-full h-full rounded-full object-cover" />
          ) : (
            name.charAt(0)
          )}
        </div>
        <div>
          <h3 className="font-bold" style={{ color: TEXT }}>
            {name}
          </h3>
          <p className="text-xs" style={{ color: TEXT_MUTED }}>
            {role}
          </p>
        </div>
      </div>
      <p className="text-sm mb-3" style={{ color: TEXT_MUTED }}>
        {description}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {skills.map((skill) => (
          <NeonBadge key={skill} variant="teal" size="sm">
            {skill}
          </NeonBadge>
        ))}
      </div>
    </NeonCard>
  );
}
