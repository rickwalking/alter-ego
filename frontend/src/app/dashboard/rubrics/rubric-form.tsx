"use client";

import { useTranslations } from "next-intl";
import { NeonFormFooter } from "@/components/molecules/neon-form-footer";
import {
  NeonDescriptionField,
  NeonEntityForm,
  NeonNameField,
} from "@/components/molecules/neon-entity-form";
import { useGuardedForm } from "@/lib/use-guarded-form";
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
  const {
    formRef,
    showErrors,
    saving,
    serverError,
    handleSubmit,
    handleCancel,
    errorOf,
  } = useGuardedForm({ form, onSave, onCancel, t });

  return (
    <NeonEntityForm
      formRef={formRef}
      idPrefix="rubric"
      title={rubric ? t("editTitle") : t("createTitle")}
      onSubmit={handleSubmit}
    >
      <NeonNameField
        id="rubric-name"
        label={t("name")}
        placeholder={t("namePlaceholder")}
        maxLength={RUBRIC_NAME_MAX}
        value={form.state.name}
        error={errorOf("name")}
        onChange={form.setName}
      />
      <NeonDescriptionField
        id="rubric-description"
        label={t("description")}
        placeholder={t("descriptionPlaceholder")}
        value={form.state.description}
        onChange={form.setDescription}
      />
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
    </NeonEntityForm>
  );
}
