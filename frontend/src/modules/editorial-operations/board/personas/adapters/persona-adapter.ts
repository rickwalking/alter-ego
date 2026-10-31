import type { NeonPersonaCardProps, PersonaProfile } from "@/modules/persona";
import { firstNonBlank } from "@/lib/utils";

/** Max expertise areas surfaced as skills on a persona card. */
const MAX_PERSONA_SKILLS = 6;

export interface PersonaSource {
  name: string;
  role: string;
  description: string;
  skills: string[];
  avatarUrl?: string;
}

export function mapPersonaToCardProps(
  persona: PersonaSource,
): NeonPersonaCardProps {
  return {
    name: persona.name,
    role: persona.role,
    description: persona.description,
    skills: persona.skills,
    avatarUrl: persona.avatarUrl,
  };
}

/** Translated texts shown when a persona leaves a card field empty. */
export interface PersonaCardFallbacks {
  /** Shown when the persona has no description nor opinion style. */
  description: string;
  /** Shown as the role when the persona has no expertise area. */
  role: string;
}

export function mapPersonaProfileToCardProps(
  profile: PersonaProfile,
  fallbacks: Readonly<PersonaCardFallbacks>,
): NeonPersonaCardProps {
  const description = firstNonBlank([
    profile.description,
    profile.opinion_expression,
    fallbacks.description,
  ]);
  const areas = profile.expertise_areas;

  return {
    name: profile.name,
    role: areas[0] ?? fallbacks.role,
    description,
    skills: areas.slice(0, MAX_PERSONA_SKILLS),
    hiddenSkills: areas.slice(MAX_PERSONA_SKILLS),
  };
}
