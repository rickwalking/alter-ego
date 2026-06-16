/**
 * Re-export shim (AE-0140). `NeonRubricCard` is a business component owned by
 * the `quality` bounded context; its canonical home is `@/modules/quality`.
 * This shim keeps the legacy `@/components/organisms/neon-rubric-card` path
 * resolving for existing importers during the Phase 7 migration window
 * (removal deferred to Phase 8). Import new code from `@/modules/quality`.
 */
export {
  NeonRubricCard,
  type NeonRubricCardProps,
} from "@/modules/quality/components/neon-rubric-card";
