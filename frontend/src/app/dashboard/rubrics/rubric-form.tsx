"use client";

import { useRef, useState } from "react";
import { flushSync } from "react-dom";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { NEON_RED } from "@/constants/neon";
import { ResourceRequestError } from "@/lib/use-resource-collection";
import { useUnsavedChangesGuard } from "@/modules/publishing";
import type {
  QualityRubric,
  QualityRubricCreatePayload,
} from "@/modules/quality";
import { RUBRIC_NAME_MAX } from "@/schemas/rubric";
import { RubricContentTypesField } from "./rubric-content-types-field";
import { RubricCriteriaList } from "./rubric-criteria-list";
import { RubricField, invalidProps } from "./rubric-field";
import { useRubricForm } from "./use-rubric-form";

const FIRST_INVALID_SELECTOR =
  'input[aria-invalid="true"], fieldset[aria-invalid="true"] input';

export interface RubricFormProps {
  /** The rubric being edited; omitted when creating one. */
  rubric?: QualityRubric;
  /** Persist the payload; a rejection keeps the form open with the reason. */
  onSave: (payload: QualityRubricCreatePayload) => Promise<void>;
  /** Leave the form without saving. */
  onCancel: () => void;
}

/** The server's own sentence when it sent one, else the translated fallback. */
function saveErrorText(err: unknown, fallback: string): string {
  return err instanceof ResourceRequestError && err.detail
    ? err.detail
    : fallback;
}

/** The rubric create/edit form: fields, criteria list, validation and save. */
export function RubricForm({
  rubric,
  onSave,
  onCancel,
}: Readonly<RubricFormProps>): React.ReactElement {
  const t = useTranslations("rubrics.form");
  const form = useRubricForm(rubric);
  const formRef = useRef<HTMLFormElement>(null);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const { confirmLeave } = useUnsavedChangesGuard(
    form.dirty,
    t("unsavedConfirm"),
  );
  const errorOf = (path: string): string | undefined => {
    const key = showErrors ? form.errors[path] : undefined;
    return key ? t(key) : undefined;
  };

  const handleSubmit = async (
    event: React.SubmitEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    flushSync(() => setShowErrors(true));
    setServerError(null);
    if (!form.isValid) {
      formRef.current
        ?.querySelector<HTMLElement>(FIRST_INVALID_SELECTOR)
        ?.focus();
      return;
    }
    setSaving(true);
    try {
      await onSave(form.toPayload());
    } catch (err) {
      setServerError(saveErrorText(err, t("errors.save")));
      setSaving(false);
    }
  };

  return (
    <form
      ref={formRef}
      noValidate
      aria-labelledby="rubric-form-title"
      className="flex max-w-3xl flex-col gap-5"
      onSubmit={(e) => void handleSubmit(e)}
    >
      <h2 id="rubric-form-title" className="text-lg font-bold">
        {rubric ? t("editTitle") : t("createTitle")}
      </h2>
      <RubricField id="rubric-name" label={t("name")} error={errorOf("name")}>
        <NeonInput
          id="rubric-name"
          value={form.state.name}
          maxLength={RUBRIC_NAME_MAX}
          autoComplete="off"
          placeholder={t("namePlaceholder")}
          {...invalidProps("rubric-name", errorOf("name"))}
          onChange={(e) => form.setName(e.target.value)}
        />
      </RubricField>
      <RubricField id="rubric-description" label={t("description")}>
        <NeonTextarea
          id="rubric-description"
          value={form.state.description}
          placeholder={t("descriptionPlaceholder")}
          onChange={(e) => form.setDescription(e.target.value)}
        />
      </RubricField>
      <RubricContentTypesField
        selected={form.state.applicable_content_types}
        error={errorOf("applicable_content_types")}
        onToggle={form.toggleContentType}
      />
      <RubricCriteriaList form={form} errorOf={errorOf} />
      {serverError && (
        <p role="alert" style={{ color: NEON_RED }} className="text-sm">
          {serverError}
        </p>
      )}
      {showErrors && !form.isValid && (
        <p role="alert" style={{ color: NEON_RED }} className="text-sm">
          {t("fixErrors")}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <NeonButton
          variant="ghost"
          onClick={() => confirmLeave() && onCancel()}
        >
          {t("cancel")}
        </NeonButton>
        <NeonButton type="submit" variant="primary" loading={saving}>
          {rubric ? t("save") : t("create")}
        </NeonButton>
      </div>
    </form>
  );
}
