import { useEffect, useRef } from "react";
import { RUBRIC_CONTENT_TYPE_CAROUSEL } from "@/constants/create";
import type { QualityRubric } from "@/modules/quality";
import type { RubricOption } from "@/app/dashboard/create/workspace/create-mode-section";

/** The rubrics the wizard offers: those applicable to carousels. */
export function carouselRubrics(
  rubrics: readonly QualityRubric[],
): RubricOption[] {
  return rubrics
    .filter((r) =>
      r.applicable_content_types.includes(RUBRIC_CONTENT_TYPE_CAROUSEL),
    )
    .map((r) => ({ id: r.id, name: r.name, isDefault: r.is_default }));
}

/**
 * Preselects the default carousel rubric once the list loads. Runs once, so a
 * deliberate other choice (or "Política padrão") is never overwritten.
 */
export function useDefaultRubric(
  rubrics: readonly RubricOption[],
  onSelect: (rubricId: string) => void,
): void {
  const applied = useRef(false);
  useEffect(() => {
    if (applied.current || rubrics.length === 0) {
      return;
    }
    applied.current = true;
    const preset = rubrics.find((r) => r.isDefault);
    if (preset) {
      onSelect(preset.id);
    }
  }, [rubrics, onSelect]);
}
