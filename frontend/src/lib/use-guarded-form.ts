"use client";

/**
 * The full submit/cancel wiring of a dashboard create/edit form: the
 * unsaved-changes guard, {@link useFormSubmit}, and translated field errors
 * that appear after the first submit. ``t`` is the form's i18n namespace and
 * must hold ``unsavedConfirm`` and ``errors.save``.
 */
import { useFormSubmit, type FormSubmit } from "@/lib/use-form-submit";
import { useUnsavedChangesGuard } from "@/modules/publishing";

export interface GuardedFormModel<P> {
  dirty: boolean;
  isValid: boolean;
  /** Field path → i18n key (in ``t``'s namespace) of its error. */
  errors: Readonly<Record<string, string>>;
  toPayload: () => P;
}

export interface GuardedFormOptions<P> {
  form: GuardedFormModel<P>;
  onSave: (payload: P) => Promise<void>;
  onCancel: () => void;
  t: (key: string) => string;
}

export interface GuardedForm extends FormSubmit {
  /** The translated error of a field path, once errors are shown. */
  errorOf: (path: string) => string | undefined;
}

export function useGuardedForm<P>({
  form,
  onSave,
  onCancel,
  t,
}: GuardedFormOptions<P>): GuardedForm {
  const { confirmLeave } = useUnsavedChangesGuard(
    form.dirty,
    t("unsavedConfirm"),
  );
  const submit = useFormSubmit({
    isValid: form.isValid,
    toPayload: form.toPayload,
    onSave,
    onCancel,
    confirmLeave,
    saveFallback: t("errors.save"),
  });
  const errorOf = (path: string): string | undefined => {
    const key = submit.showErrors ? form.errors[path] : undefined;
    return key ? t(key) : undefined;
  };
  return { ...submit, errorOf };
}
