/**
 * Persona component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */
import type { ReactNode } from "react";

export interface NeonPersonaCardProps {
  name: string;
  role: string;
  description: string;
  skills: string[];
  avatarUrl?: string;
  /** Expertise areas not shown as chips; summarised by a "+N" chip. */
  hiddenSkills?: string[];
  /** Actions rendered in the card footer (e.g. Edit and Delete). */
  footer?: ReactNode;
}

export interface VoiceMatchScorerProps {
  personaId: string;
}
