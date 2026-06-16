/**
 * `persona` — bounded-context public contract (AE-0139).
 *
 * Owns the persona surface — persona profile types, the persona-management hook,
 * and the voice-match scorer — CONSOLIDATING the previously duplicated legacy
 * `features/persona` and `features/personas` folders into a single module. This
 * barrel is the ONLY import surface for cross-context and `app/` consumers
 * (notably the `quality` module, which depends on `persona` ONLY via this
 * contract); everything else under `modules/persona/**` is internal.
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

/* --- types --- */
export type {
  ToneAttributes,
  PersonaProfile,
  PersonaCreatePayload,
  PersonaUpdatePayload,
  FeedbackPayload,
} from "./types";

/* --- hooks --- */
export { usePersonas } from "./hooks/use-personas";

/* --- components --- */
export { VoiceMatchScorer } from "./components/voice-match-scorer";
