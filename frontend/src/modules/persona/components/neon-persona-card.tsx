import Image from "next/image";
import { UserRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import {
  NEON_BORDER_FOCUS,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_MUTED,
} from "@/constants/neon";
import { personaInitial } from "./persona-initial";
import type { NeonPersonaCardProps } from "./types";

/** Avatar square dimensions (px) matching the w-12 h-12 container. */
const PERSONA_AVATAR_SIZE = 48;
/** Fallback avatar icon size (px) inside the 48 px avatar. */
const PERSONA_AVATAR_ICON_SIZE = 22;
/** Joins the hidden expertise areas in the "+N" chip tooltip and label. */
const SKILL_LIST_SEPARATOR = ", ";

type AvatarProps = Pick<NeonPersonaCardProps, "name" | "avatarUrl">;

/** The avatar content: the photo, the first letter, or a labelled icon. */
function AvatarContent({
  name,
  avatarUrl,
}: Readonly<AvatarProps>): React.ReactElement {
  const t = useTranslations("personas.card");
  if (avatarUrl) {
    return (
      <Image
        src={avatarUrl}
        alt=""
        width={PERSONA_AVATAR_SIZE}
        height={PERSONA_AVATAR_SIZE}
        className="w-full h-full rounded-full object-cover"
        unoptimized
      />
    );
  }
  const initial = personaInitial(name);
  if (initial) {
    return <span aria-hidden="true">{initial}</span>;
  }
  return (
    <UserRound
      role="img"
      aria-label={t("avatarLabel", { name })}
      size={PERSONA_AVATAR_ICON_SIZE}
    />
  );
}

/** A persona summary: avatar, name, role, description, expertise and actions. */
export function NeonPersonaCard({
  name,
  role,
  description,
  skills,
  avatarUrl,
  hiddenSkills = [],
  footer,
}: Readonly<NeonPersonaCardProps>): React.ReactElement {
  const t = useTranslations("personas.card");
  return (
    <NeonCard padding="md" className="flex h-full flex-col">
      <div className="flex items-start gap-4 mb-3">
        <div
          data-testid="persona-avatar"
          className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold shrink-0"
          style={{
            background: NEON_CYAN_DIM,
            color: NEON_CYAN,
            border: `1px solid ${NEON_BORDER_FOCUS}`,
          }}
        >
          <AvatarContent name={name} avatarUrl={avatarUrl} />
        </div>
        <div className="min-w-0">
          <h3 className="font-bold break-words" style={{ color: TEXT }}>
            {name}
          </h3>
          <p className="text-xs break-words" style={{ color: TEXT_MUTED }}>
            {role}
          </p>
        </div>
      </div>
      <p className="text-sm mb-3 break-words" style={{ color: TEXT_MUTED }}>
        {description}
      </p>
      <ul className="flex flex-wrap gap-1.5" aria-label={t("skillsLabel")}>
        {skills.map((skill) => (
          <li key={skill}>
            <NeonBadge variant="teal" size="md">
              {skill}
            </NeonBadge>
          </li>
        ))}
        {hiddenSkills.length > 0 && (
          <li title={hiddenSkills.join(SKILL_LIST_SEPARATOR)}>
            <NeonBadge variant="teal" size="md" outline>
              <span aria-hidden="true">+{hiddenSkills.length}</span>
              <span className="sr-only">
                {t("moreSkills", {
                  count: hiddenSkills.length,
                  areas: hiddenSkills.join(SKILL_LIST_SEPARATOR),
                })}
              </span>
            </NeonBadge>
          </li>
        )}
      </ul>
      {footer && (
        <div className="mt-auto flex justify-end gap-1 pt-3">{footer}</div>
      )}
    </NeonCard>
  );
}
