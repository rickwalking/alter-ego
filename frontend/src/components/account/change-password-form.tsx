"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonFormField } from "@/components/molecules/neon-form-field";
import { USER_PASSWORD_MIN_LENGTH } from "@/constants/admin-users";
import {
  BG_CARD,
  NEON_BORDER_SUBTLE,
  NEON_GREEN,
  NEON_RED,
} from "@/constants/neon";
import type {
  ChangePasswordController,
  PasswordChangeValues,
} from "@/modules/identity";

const AUTOCOMPLETE_CURRENT = "current-password";
const AUTOCOMPLETE_NEW = "new-password";
const ALERT_STYLE = {
  padding: "10px 14px",
  borderRadius: "6px",
  fontSize: "13px",
} as const;
const ERROR_BACKGROUND = "rgba(239,68,68,0.12)";
const SUCCESS_BACKGROUND = "rgba(34,197,94,0.12)";

/** One password input of the form, labelled and wired to the controller. */
interface PasswordFieldProps {
  field: keyof PasswordChangeValues;
  label: string;
  autoComplete: string;
  hint?: string;
  controller: ChangePasswordController;
}

function PasswordField({
  field,
  label,
  autoComplete,
  hint,
  controller,
}: Readonly<PasswordFieldProps>): React.ReactElement {
  const id = `password-${field}`;
  return (
    <NeonFormField label={label} name={id} hint={hint} required>
      <NeonInput
        id={id}
        name={id}
        type="password"
        required
        autoComplete={autoComplete}
        value={controller.values[field]}
        onChange={(e) => controller.setField(field, e.target.value)}
      />
    </NeonFormField>
  );
}

/** The result line above the fields: the error or the success message. */
function FormStatus({
  controller,
}: Readonly<{
  controller: ChangePasswordController;
}>): React.ReactElement | null {
  const t = useTranslations("account.password");
  if (controller.errorKey !== null) {
    return (
      <div
        role="alert"
        style={{
          ...ALERT_STYLE,
          background: ERROR_BACKGROUND,
          color: NEON_RED,
        }}
      >
        {t(`errors.${controller.errorKey}`, { min: USER_PASSWORD_MIN_LENGTH })}
      </div>
    );
  }
  if (!controller.succeeded) {
    return null;
  }
  return (
    <div
      role="status"
      style={{
        ...ALERT_STYLE,
        background: SUCCESS_BACKGROUND,
        color: NEON_GREEN,
      }}
    >
      {t("success")}
    </div>
  );
}

/**
 * The change-password form (current, new, confirm). Presentation only: the
 * state and the request live in `useChangePassword`. A forced change (after an
 * admin reset) explains why the user cannot continue yet. It is a POST form so
 * a submit before hydration never puts the passwords in a GET URL.
 */
export function ChangePasswordForm({
  controller,
  forced,
}: Readonly<{
  controller: ChangePasswordController;
  forced: boolean;
}>): React.ReactElement {
  const t = useTranslations("account.password");
  return (
    <form
      method="post"
      onSubmit={(e) => {
        void controller.handleSubmit(e);
      }}
      className="space-y-5"
      style={{
        background: BG_CARD,
        border: `1px solid ${NEON_BORDER_SUBTLE}`,
        borderRadius: "8px",
        padding: "24px",
      }}
    >
      <p className="text-sm text-text-secondary">
        {forced ? t("forcedNotice") : t("description")}
      </p>
      <FormStatus controller={controller} />
      <PasswordField
        field="current"
        label={forced ? t("temporaryLabel") : t("currentLabel")}
        autoComplete={AUTOCOMPLETE_CURRENT}
        controller={controller}
      />
      <PasswordField
        field="next"
        label={t("newLabel")}
        hint={t("newHint", { min: USER_PASSWORD_MIN_LENGTH })}
        autoComplete={AUTOCOMPLETE_NEW}
        controller={controller}
      />
      <PasswordField
        field="confirm"
        label={t("confirmLabel")}
        autoComplete={AUTOCOMPLETE_NEW}
        controller={controller}
      />
      <NeonButton
        type="submit"
        loading={controller.isLoading}
        disabled={controller.isLoading}
      >
        {controller.isLoading ? t("saving") : t("submit")}
      </NeonButton>
    </form>
  );
}
