import type { NeonPersonaCardProps, PersonaProfile } from "@/modules/persona";

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

export function mapPersonaProfileToCardProps(
  profile: PersonaProfile,
): NeonPersonaCardProps {
  const description =
    profile.description?.trim() ||
    profile.opinion_expression?.trim() ||
    "No description provided.";

  return {
    name: profile.name,
    role: profile.expertise_areas[0] ?? "Persona",
    description,
    skills: profile.expertise_areas.slice(0, MAX_PERSONA_SKILLS),
  };
}
