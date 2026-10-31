"use client";

import { useTranslations } from "next-intl";
import { NeonConfirmDialog } from "@/components/molecules/neon-confirm-dialog";
import { NeonFormFooter } from "@/components/molecules/neon-form-footer";
import {
  NeonDescriptionField,
  NeonEntityForm,
  NeonNameField,
} from "@/components/molecules/neon-entity-form";
import { useGuardedForm } from "@/lib/use-guarded-form";
import { useLeaveConfirm, type LeaveConfirm } from "@/lib/use-leave-confirm";
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

interface LeaveDialogProps {
  leave: LeaveConfirm;
}

/** Asks in an in-app dialog before the form drops its unsaved changes. */
function LeaveDialog({
  leave,
}: Readonly<LeaveDialogProps>): React.ReactElement | null {
  const t = useTranslations("rubrics.form");
  if (!leave.open) {
    return null;
  }
  return (
    <NeonConfirmDialog
      title={t("leaveTitle")}
      body={t("unsavedConfirm")}
      confirmLabel={t("leaveConfirm")}
      cancelLabel={t("leaveStay")}
      errorFallback={t("errors.save")}
      onConfirm={leave.confirm}
      onClose={leave.stay}
    />
  );
}

/**
 * The rubric create/edit form: fields, criteria list, validation and save.
 * Cancel and Escape leave it, through the leave dialog when it has changes.
 */
export function RubricForm({
  rubric,
  onSave,
  onCancel,
}: Readonly<RubricFormProps>): React.ReactElement {
  const t = useTranslations("rubrics.form");
  const form = useRubricForm(rubric);
  const { formRef, showErrors, saving, serverError, handleSubmit, errorOf } =
    useGuardedForm({ form, onSave, onCancel, t });
  const leave = useLeaveConfirm(formRef, form.dirty, onCancel);

  return (
    <>
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
          onCancel={leave.request}
        />
      </NeonEntityForm>
      <LeaveDialog leave={leave} />
    </>
  );
}
