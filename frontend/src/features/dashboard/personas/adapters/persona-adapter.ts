import type { NeonPersonaCardProps } from "@/components/organisms/neon-persona-card";
import type { PersonaProfile } from "@/features/persona/types";

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
    skills: profile.expertise_areas.slice(0, 6),
  };
}
