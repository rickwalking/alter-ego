import type { NeonPersonaCardProps } from "@/components/organisms/neon-persona-card";

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
