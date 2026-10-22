"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonSelect } from "@/components/atoms/neon-select";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { EVALUATION_METHODS, SCORING_SCALES } from "@/schemas/rubric";
import type { CriterionDraft } from "./rubric-form-model";
import {
  NeonLabelledField,
  invalidProps,
} from "@/components/molecules/neon-labelled-field";
import type { CriterionEdit } from "./use-rubric-form";

const PROMPT_TOKEN = "{content}";
const UNIT_STEP = "0.05";

type CriterionField = CriterionEdit["field"];

interface RubricCriterionFieldsProps {
  criterion: CriterionDraft;
  index: number;
  count: number;
  /** The translated error of a field of this criterion, if shown. */
  errorOf: (field: CriterionField) => string | undefined;
  onChange: (edit: CriterionEdit) => void;
  onMove: (offset: number) => void;
  onRemove: () => void;
  /** Focus the name field when it mounts (a criterion the user just added). */
  focusOnMount: boolean;
}

function CriterionToolbar({
  index,
  count,
  onMove,
  onRemove,
}: Readonly<
  Pick<RubricCriterionFieldsProps, "index" | "count" | "onMove" | "onRemove">
>): React.ReactElement {
  const t = useTranslations("rubrics");
  const number = index + 1;
  return (
    <div className="flex gap-1">
      <NeonButton
        variant="ghost"
        size="sm"
        disabled={index === 0}
        aria-label={t("form.moveUp", { number })}
        onClick={() => onMove(-1)}
      >
        ↑
      </NeonButton>
      <NeonButton
        variant="ghost"
        size="sm"
        disabled={index === count - 1}
        aria-label={t("form.moveDown", { number })}
        onClick={() => onMove(1)}
      >
        ↓
      </NeonButton>
      <NeonButton
        variant="ghost"
        size="sm"
        aria-label={t("form.remove", { number })}
        onClick={onRemove}
      >
        ✕
      </NeonButton>
    </div>
  );
}

/** One criterion of the rubric form: its fields plus reorder/remove controls. */
export function RubricCriterionFields(
  props: Readonly<RubricCriterionFieldsProps>,
): React.ReactElement {
  const { criterion, index, errorOf, onChange, focusOnMount } = props;
  const t = useTranslations("rubrics");
  const nameRef = useRef<HTMLInputElement>(null);
  const id = (field: string): string => `criterion-${criterion.id}-${field}`;
  const set = (field: CriterionField) => (value: string) =>
    onChange({ index, field, value });

  useEffect(() => {
    if (focusOnMount) nameRef.current?.focus();
  }, [focusOnMount]);

  return (
    <fieldset className="flex flex-col gap-3 rounded-lg border border-white/10 p-4">
      <legend className="float-left pt-1.5 text-sm font-semibold text-text-primary">
        {t("form.criterionLegend", { number: index + 1 })}
      </legend>
      <div className="flex justify-end">
        <CriterionToolbar {...props} />
      </div>
      <NeonLabelledField
        id={id("name")}
        label={t("form.criterionName")}
        error={errorOf("name")}
      >
        <NeonInput
          ref={nameRef}
          id={id("name")}
          value={criterion.name}
          autoComplete="off"
          {...invalidProps(id("name"), errorOf("name"))}
          onChange={(e) => set("name")(e.target.value)}
        />
      </NeonLabelledField>
      <NeonLabelledField
        id={id("description")}
        label={t("form.criterionDescription")}
      >
        <NeonInput
          id={id("description")}
          value={criterion.description}
          autoComplete="off"
          onChange={(e) => set("description")(e.target.value)}
        />
      </NeonLabelledField>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <NeonLabelledField
          id={id("weight")}
          label={t("form.weight")}
          error={errorOf("weight")}
        >
          <NeonInput
            id={id("weight")}
            type="number"
            inputMode="decimal"
            min={0}
            max={1}
            step={UNIT_STEP}
            value={criterion.weight}
            {...invalidProps(id("weight"), errorOf("weight"))}
            onChange={(e) => set("weight")(e.target.value)}
          />
        </NeonLabelledField>
        <NeonLabelledField
          id={id("min_threshold")}
          label={t("form.minThreshold")}
          error={errorOf("min_threshold")}
        >
          <NeonInput
            id={id("min_threshold")}
            type="number"
            inputMode="decimal"
            min={0}
            max={1}
            step={UNIT_STEP}
            value={criterion.min_threshold}
            {...invalidProps(id("min_threshold"), errorOf("min_threshold"))}
            onChange={(e) => set("min_threshold")(e.target.value)}
          />
        </NeonLabelledField>
        <NeonLabelledField
          id={id("evaluation_method")}
          label={t("form.evaluationMethod")}
        >
          <NeonSelect
            id={id("evaluation_method")}
            value={criterion.evaluation_method}
            onChange={(e) => set("evaluation_method")(e.target.value)}
          >
            {EVALUATION_METHODS.map((method) => (
              <option key={method} value={method}>
                {t(`evaluationMethod.${method}`)}
              </option>
            ))}
          </NeonSelect>
        </NeonLabelledField>
        <NeonLabelledField
          id={id("scoring_scale")}
          label={t("form.scoringScale")}
        >
          <NeonSelect
            id={id("scoring_scale")}
            value={criterion.scoring_scale}
            onChange={(e) => set("scoring_scale")(e.target.value)}
          >
            {SCORING_SCALES.map((scale) => (
              <option key={scale} value={scale}>
                {t(`scoringScale.${scale}`)}
              </option>
            ))}
          </NeonSelect>
        </NeonLabelledField>
      </div>
      <NeonLabelledField
        id={id("prompt_template")}
        label={t("form.promptTemplate")}
        hint={t("form.promptHint", { token: PROMPT_TOKEN })}
      >
        <NeonTextarea
          id={id("prompt_template")}
          value={criterion.prompt_template}
          onChange={(e) => set("prompt_template")(e.target.value)}
        />
      </NeonLabelledField>
    </fieldset>
  );
}
