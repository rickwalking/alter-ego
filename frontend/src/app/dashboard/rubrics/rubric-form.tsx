"use client";

import { useTranslations } from "next-intl";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { NeonFormFooter } from "@/components/molecules/neon-form-footer";
import {
  NeonLabelledField,
  invalidProps,
} from "@/components/molecules/neon-labelled-field";
import { useFormSubmit } from "@/lib/use-form-submit";
import { useUnsavedChangesGuard } from "@/modules/publishing";
import type {
  QualityRubric,
  QualityRubricCreatePayload,
} from "@/modules/quality";
import { RUBRIC_NAME_MAX } from "@/schemas/rubric";
import { RubricContentTypesField } from "./rubric-content-types-field";
import { RubricCriteriaList } from "./rubric-criteria-list";
import { useRubricForm } from "./use-rubric-form";

export interface RubricFormProps {
  /** The rubric being edited; omitted when creating one. */
  rubric?: QualityRubric;
  /** Persist the payload; a rejection keeps the form open with the reason. */
  onSave: (payload: QualityRubricCreatePayload) => Promise<void>;
  /** Leave the form without saving. */
  onCancel: () => void;
}

/** The rubric create/edit form: fields, criteria list, validation and save. */
export function RubricForm({
  rubric,
  onSave,
  onCancel,
}: Readonly<RubricFormProps>): React.ReactElement {
  const t = useTranslations("rubrics.form");
  const form = useRubricForm(rubric);
  const { confirmLeave } = useUnsavedChangesGuard(
    form.dirty,
    t("unsavedConfirm"),
  );
  const {
    formRef,
    showErrors,
    saving,
    serverError,
    handleSubmit,
    handleCancel,
  } = useFormSubmit({
    isValid: form.isValid,
    toPayload: form.toPayload,
    onSave,
    onCancel,
    confirmLeave,
    saveFallback: t("errors.save"),
  });
  const errorOf = (path: string): string | undefined => {
    const key = showErrors ? form.errors[path] : undefined;
    return key ? t(key) : undefined;
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
      <NeonLabelledField
        id="rubric-name"
        label={t("name")}
        error={errorOf("name")}
      >
        <NeonInput
          id="rubric-name"
          value={form.state.name}
          maxLength={RUBRIC_NAME_MAX}
          autoComplete="off"
          placeholder={t("namePlaceholder")}
          {...invalidProps("rubric-name", errorOf("name"))}
          onChange={(e) => form.setName(e.target.value)}
        />
      </NeonLabelledField>
      <NeonLabelledField id="rubric-description" label={t("description")}>
        <NeonTextarea
          id="rubric-description"
          value={form.state.description}
          placeholder={t("descriptionPlaceholder")}
          onChange={(e) => form.setDescription(e.target.value)}
        />
      </NeonLabelledField>
      <RubricContentTypesField
        selected={form.state.applicable_content_types}
        error={errorOf("applicable_content_types")}
        onToggle={form.toggleContentType}
      />
      <RubricCriteriaList form={form} errorOf={errorOf} />
      <NeonFormFooter
        serverError={serverError}
        invalidMessage={showErrors && !form.isValid ? t("fixErrors") : null}
        cancelLabel={t("cancel")}
        submitLabel={rubric ? t("save") : t("create")}
        saving={saving}
        onCancel={handleCancel}
      />
    </form>
  );
}
