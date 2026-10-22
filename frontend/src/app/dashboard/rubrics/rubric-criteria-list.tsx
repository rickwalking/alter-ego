"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NEON_RED } from "@/constants/neon";
import { RubricCriterionFields } from "./rubric-criterion-fields";
import type { UseRubricFormResult } from "./use-rubric-form";

interface RubricCriteriaListProps {
  form: UseRubricFormResult;
  /** The translated error of a field path, if errors are shown. */
  errorOf: (path: string) => string | undefined;
}

/** The criteria section of the rubric form: each criterion plus "add". */
export function RubricCriteriaList({
  form,
  errorOf,
}: Readonly<RubricCriteriaListProps>): React.ReactElement {
  const t = useTranslations("rubrics.form");
  const { criteria } = form.state;
  const listError = errorOf("criteria");
  return (
    <section
      aria-labelledby="rubric-criteria-title"
      className="flex flex-col gap-3"
    >
      <h3 id="rubric-criteria-title" className="text-sm font-semibold">
        {t("criteria")}
      </h3>
      {criteria.length === 0 && (
        <p className="text-xs text-text-muted">{t("noCriteria")}</p>
      )}
      {listError && (
        <p className="text-xs" style={{ color: NEON_RED }}>
          {listError}
        </p>
      )}
      {criteria.map((criterion, index) => (
        <RubricCriterionFields
          key={criterion.id}
          criterion={criterion}
          index={index}
          count={criteria.length}
          errorOf={(field) => errorOf(`criteria.${index}.${field}`)}
          onChange={form.setCriterionField}
          onMove={(offset) => form.moveCriterion(index, offset)}
          onRemove={() => form.removeCriterion(index)}
          focusOnMount={criterion.id === form.addedId}
        />
      ))}
      <div>
        <NeonButton variant="secondary" size="sm" onClick={form.addCriterion}>
          {t("addCriterion")}
        </NeonButton>
      </div>
    </section>
  );
}
