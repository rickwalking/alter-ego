"use client";

/**
 * Submit/cancel flow shared by the dashboard create/edit forms (rubrics,
 * personas): show field errors and focus the first invalid control on a
 * blocked submit, keep a save failure (the API's sentence, or a fallback)
 * next to the form, and ask before Cancel discards changes.
 */
import { useRef, useState, type RefObject } from "react";
import { flushSync } from "react-dom";
import { requestErrorText } from "@/lib/use-resource-collection";

const FIRST_INVALID_SELECTOR = [
  'input[aria-invalid="true"]',
  'textarea[aria-invalid="true"]',
  'fieldset[aria-invalid="true"] input',
].join(", ");

export interface FormSubmitOptions<P> {
  isValid: boolean;
  toPayload: () => P;
  /** Persist the payload; a rejection keeps the form open with the reason. */
  onSave: (payload: P) => Promise<void>;
  onCancel: () => void;
  /** Asks before discarding changes; true when leaving is fine. */
  confirmLeave: () => boolean;
  /** Shown when a save fails without a message of its own. */
  saveFallback: string;
}

type SubmitEvent = React.SubmitEvent<HTMLFormElement>;

export interface FormSubmit {
  formRef: RefObject<HTMLFormElement | null>;
  /** True after the first submit: field errors are visible from then on. */
  showErrors: boolean;
  saving: boolean;
  serverError: string | null;
  handleSubmit: (event: SubmitEvent) => Promise<void>;
  handleCancel: () => void;
}

interface SubmitContext<P> {
  options: FormSubmitOptions<P>;
  form: HTMLFormElement | null;
  setShowErrors: (value: boolean) => void;
  setSaving: (value: boolean) => void;
  setServerError: (value: string | null) => void;
}

async function submitForm<P>(ctx: SubmitContext<P>): Promise<void> {
  const { options } = ctx;
  flushSync(() => ctx.setShowErrors(true));
  ctx.setServerError(null);
  if (!options.isValid) {
    ctx.form?.querySelector<HTMLElement>(FIRST_INVALID_SELECTOR)?.focus();
    return;
  }
  ctx.setSaving(true);
  try {
    await options.onSave(options.toPayload());
  } catch (err) {
    ctx.setServerError(requestErrorText(err, options.saveFallback));
    ctx.setSaving(false);
  }
}

export function useFormSubmit<P>(options: FormSubmitOptions<P>): FormSubmit {
  const formRef = useRef<HTMLFormElement>(null);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const handleSubmit = async (event: SubmitEvent): Promise<void> => {
    event.preventDefault();
    const form = formRef.current;
    await submitForm({
      options,
      form,
      setShowErrors,
      setSaving,
      setServerError,
    });
  };

  return {
    formRef,
    showErrors,
    saving,
    serverError,
    handleSubmit,
    handleCancel: () => {
      if (options.confirmLeave()) options.onCancel();
    },
  };
}
