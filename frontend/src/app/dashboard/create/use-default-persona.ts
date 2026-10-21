import { useEffect, useRef } from "react";
import { DEFAULT_PERSONA_NAME } from "@/constants/create";
import type { PersonaOption } from "@/app/dashboard/create/workspace/create-mode-section";

/** The id of the persona named "Pedro" (case-insensitive), or "" when absent. */
export function defaultPersonaId(personas: readonly PersonaOption[]): string {
  const wanted = DEFAULT_PERSONA_NAME.toLocaleLowerCase();
  const match = personas.find(
    (p) => p.name.trim().toLocaleLowerCase() === wanted,
  );
  return match?.id ?? "";
}

/**
 * Preselects the "Pedro" persona once the list
 * loads. Runs once, so a deliberate "no persona" choice is never overwritten.
 */
export function useDefaultPersona(
  personas: readonly PersonaOption[],
  onSelect: (personaId: string) => void,
): void {
  const applied = useRef(false);
  useEffect(() => {
    if (applied.current || personas.length === 0) {
      return;
    }
    applied.current = true;
    const id = defaultPersonaId(personas);
    if (id) {
      onSelect(id);
    }
  }, [personas, onSelect]);
}
