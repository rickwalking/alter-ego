"use client";

import { useTranslations } from "next-intl";
import { USER_PASSWORD_MIN_LENGTH } from "@/constants/admin-users";
import { PasswordInput } from "./password-input";
import {
  DIALOG_MUTED_TEXT_CLASS,
  FIELD_ERROR_CLASS,
  FIELD_LABEL_CLASS,
} from "./user-dialog-parts";

interface PasswordFieldProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

/**
 * The optional password: its 12-character minimum is said up front as a hint,
 * and a too-short value shows a message under the field.
 */
export function CreatePasswordField({
  id,
  value,
  onChange,
  error,
}: Readonly<PasswordFieldProps>) {
  const t = useTranslations("admin");
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = error === undefined ? hintId : `${hintId} ${errorId}`;
  return (
    <div>
      <label htmlFor={id} className={FIELD_LABEL_CLASS}>
        {t("passwordLabel")}
        <span className="ml-1 text-xs text-text-muted">
          ({t("passwordOptional")})
        </span>
      </label>
      <PasswordInput
        id={id}
        value={value}
        onChange={onChange}
        placeholder={t("passwordPlaceholder")}
        describedBy={describedBy}
        invalid={error !== undefined}
      />
      <p id={hintId} className={`mt-1 ${DIALOG_MUTED_TEXT_CLASS}`}>
        {t("passwordHint", { min: USER_PASSWORD_MIN_LENGTH })}
      </p>
      {error !== undefined && (
        <p id={errorId} className={FIELD_ERROR_CLASS}>
          {error}
        </p>
      )}
    </div>
  );
}
