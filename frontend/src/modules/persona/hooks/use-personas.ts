/**
 * Custom hook for managing persona profiles
 */

import {
  useResourceCollection,
  type ResourceCollection,
} from "@/lib/use-resource-collection";
import type {
  PersonaProfile,
  PersonaCreatePayload,
  PersonaUpdatePayload,
} from "@/modules/persona/types";

type PersonasCollection = Omit<
  ResourceCollection<
    PersonaProfile,
    PersonaCreatePayload,
    PersonaUpdatePayload
  >,
  "items"
> & { personas: PersonaProfile[] };

/** The personas collection (list, create, update, delete). */
export function usePersonas(): PersonasCollection {
  const { items, ...rest } = useResourceCollection<
    PersonaProfile,
    PersonaCreatePayload,
    PersonaUpdatePayload
  >({
    path: "personas",
    noun: "persona",
  });
  return { personas: items, ...rest };
}
