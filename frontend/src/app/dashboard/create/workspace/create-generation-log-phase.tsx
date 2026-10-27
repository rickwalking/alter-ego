"use client";

import { useTranslations } from "next-intl";
import { usePhaseLabel } from "./editorial-phase-labels";
import { GenerationEventRow } from "./create-generation-log-event";
import {
  generationPhaseBase,
  type GenerationLogPhaseGroup,
} from "./create-generation-log-model";

const SPECIAL_PHASES = new Set(["run", "start", "export", "recovery"]);

interface GenerationPhaseProps {
  group: GenerationLogPhaseGroup;
}

export function GenerationPhase({ group }: Readonly<GenerationPhaseProps>) {
  const t = useTranslations("create.generationLog");
  const phaseLabel = usePhaseLabel();
  const base = group.phase ? generationPhaseBase(group.phase) : "run";
  const title = SPECIAL_PHASES.has(base)
    ? t(`phases.${base}`)
    : phaseLabel(base);
  return (
    <section aria-label={title} className="border-l border-white/15 pl-2">
      <h4 className="mb-1 font-semibold text-text-primary">{title}</h4>
      <ol className="space-y-2">
        {group.events.map((event) => (
          <GenerationEventRow key={event.id} event={event} />
        ))}
      </ol>
    </section>
  );
}
