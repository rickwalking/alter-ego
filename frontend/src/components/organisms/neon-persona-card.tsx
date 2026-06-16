/**
 * Re-export shim (AE-0140). `NeonPersonaCard` is a business component owned by
 * the `persona` bounded context; its canonical home is `@/modules/persona`.
 * This shim keeps the legacy `@/components/organisms/neon-persona-card` path
 * resolving for existing importers during the Phase 7 migration window
 * (removal deferred to Phase 8). Import new code from `@/modules/persona`.
 */
export {
  NeonPersonaCard,
  type NeonPersonaCardProps,
} from "@/modules/persona/components/neon-persona-card";
