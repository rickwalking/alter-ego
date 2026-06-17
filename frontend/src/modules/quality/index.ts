/**
 * `quality` — bounded-context public contract (AE-0139).
 *
 * Owns the quality-rubric surface — rubric types and the rubric-management hook
 * — migrated from the legacy `features/rubrics` folder. `quality` is a SEPARATE
 * context from `persona` (the forbidden `persona_quality` module does NOT
 * exist); when `quality` needs persona it depends on it ONE-WAY, through the
 * `@/modules/persona` public contract only. This barrel is the ONLY import
 * surface for cross-context and `app/` consumers; everything else under
 * `modules/quality/**` is internal.
 *
 * See `src/modules/README.md` for the public-contract convention and
 * `docs/architecture/domain-glossary.md` for the persona ⟶ quality boundary.
 */

/* --- types --- */
export type {
  RubricCriterion,
  QualityRubric,
  QualityRubricCreatePayload,
  QualityRubricUpdatePayload,
  RubricEvaluationScore,
  RubricEvaluationResponse,
} from "./types";

/* --- hooks --- */
export { useRubrics } from "./hooks/use-rubrics";

/* --- components --- */
export { NeonRubricCard } from "./components/neon-rubric-card";
export type { NeonRubricCardProps } from "./components/types";
