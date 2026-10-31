"use client";

import { useTranslations } from "next-intl";
import { NEON_RED } from "@/constants/neon";
import { contentTypeOptions } from "./rubric-form-model";
import { useContentTypeLabel } from "./use-rubric-labels";
import { fieldErrorId } from "@/components/molecules/neon-labelled-field";

const FIELD_ID = "rubric-content-types";

interface RubricContentTypesFieldProps {
  selected: readonly string[];
  error?: string;
  onToggle: (type: string) => void;
}

/** The "applies to" checkbox group of the rubric form. */
export function RubricContentTypesField({
  selected,
  error,
  onToggle,
}: Readonly<RubricContentTypesFieldProps>): React.ReactElement {
  const t = useTranslations("rubrics.form");
  const label = useContentTypeLabel();
  return (
    <fieldset
      className="flex flex-col gap-2"
      aria-invalid={error !== undefined}
      aria-describedby={error ? fieldErrorId(FIELD_ID) : undefined}
    >
      <legend className="mb-1 text-xs text-text-muted">
        {t("contentTypes")}
      </legend>
      <div className="flex flex-wrap gap-4">
        {contentTypeOptions(selected).map((type) => (
          <label key={type} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={selected.includes(type)}
              onChange={() => onToggle(type)}
              className="h-4 w-4 accent-[var(--color-neon-cyan)]"
            />
            {label(type)}
          </label>
        ))}
      </div>
      {error && (
        <p
          id={fieldErrorId(FIELD_ID)}
          className="text-xs"
          style={{ color: NEON_RED }}
        >
          {error}
        </p>
      )}
    </fieldset>
  );
}
