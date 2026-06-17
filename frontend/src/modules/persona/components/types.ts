/**
 * Persona component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

export interface NeonPersonaCardProps {
  name: string;
  role: string;
  description: string;
  skills: string[];
  avatarUrl?: string;
}

export interface VoiceMatchScorerProps {
  personaId: string;
}
