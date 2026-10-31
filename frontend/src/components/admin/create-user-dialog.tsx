"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import {
  USER_PASSWORD_FIELD,
  USER_PASSWORD_MIN_LENGTH,
} from "@/constants/admin-users";
import {
  adminErrorKey,
  type CreateFieldErrors,
  CREATE_FIELD_MESSAGE_KEYS,
  createFieldErrors,
  isPasswordTooShort,
} from "@/lib/admin-user-errors";
import { responseErrorBody } from "@/lib/response-error";
import { CreatePasswordField } from "./create-password-field";
import {
  UserDialogActions,
  UserDialogShell,
  useDialogStatus,
  UserRoleSelect,
} from "./user-dialog-parts";
import { UserFormField } from "./user-form-field";

const CREATE_USERS_URL = "/api/admin/users";
const AUTOCOMPLETE_EMAIL = "email";
const AUTOCOMPLETE_NAME = "name";
const SUCCESS_CLOSE_DELAY_MS = 2000;

interface CreateUserDialogProps {
  onClose: () => void;
  onSuccess: () => void;
}

/** What the create request ended in: a success, or keys to translate. */
type CreateOutcome =
  | { ok: true; tempPassword?: string }
  | { ok: false; fields: CreateFieldErrors; messageKey?: string };

/** POST the new user; a failure comes back as message keys, never English text. */
async function requestCreateUser(
  payload: Record<string, string>,
): Promise<CreateOutcome> {
  const response = await fetch(CREATE_USERS_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (response.ok) {
    const data = (await response.json()) as { temp_password?: string };
    return { ok: true, tempPassword: data.temp_password };
  }
  const body = await responseErrorBody(response);
  return {
    ok: false,
    fields: createFieldErrors(response.status, body),
    messageKey: adminErrorKey(response.status, body),
  };
}

function buildPayload(
  fields: Record<string, string>,
  password: string,
): Record<string, string> {
  return password ? { ...fields, password } : fields;
}

export function CreateUserDialog({
  onClose,
  onSuccess,
}: Readonly<CreateUserDialogProps>) {
  const t = useTranslations("admin");
  const fieldId = useId();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("editor");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<CreateFieldErrors>({});
  const status = useDialogStatus();
  const fieldError = (key?: string): string | undefined =>
    key === undefined ? undefined : t(key, { min: USER_PASSWORD_MIN_LENGTH });

  const showOutcome = (outcome: CreateOutcome): void => {
    if (!outcome.ok) {
      setFieldErrors(outcome.fields);
      const hasFieldErrors = Object.keys(outcome.fields).length > 0;
      if (!hasFieldErrors)
        status.setError(t(outcome.messageKey ?? "createError"));
      return;
    }
    status.setSuccess(
      outcome.tempPassword
        ? t("createSuccessWithPassword", { password: outcome.tempPassword })
        : t("createSuccess"),
    );
    setTimeout(onSuccess, SUCCESS_CLOSE_DELAY_MS);
  };

  const handleSubmit = async (e: React.SubmitEvent) => {
    e.preventDefault();
    if (isPasswordTooShort(password)) {
      setFieldErrors({
        [USER_PASSWORD_FIELD]: CREATE_FIELD_MESSAGE_KEYS[USER_PASSWORD_FIELD],
      });
      return;
    }
    setFieldErrors({});
    status.begin();
    try {
      const fields = { email, full_name: fullName, role };
      showOutcome(await requestCreateUser(buildPayload(fields, password)));
    } catch {
      status.setError(t("createError"));
    } finally {
      status.finish();
    }
  };

  return (
    <UserDialogShell
      title={t("createUserTitle")}
      onClose={onClose}
      error={status.error}
      success={status.success}
    >
      <form
        method="post"
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="mt-4 space-y-4"
      >
        <UserFormField
          id={`${fieldId}-email`}
          label={t("emailLabel")}
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete={AUTOCOMPLETE_EMAIL}
          error={fieldError(fieldErrors.email)}
        />

        <UserFormField
          id={`${fieldId}-full-name`}
          label={t("fullNameLabel")}
          type="text"
          value={fullName}
          onChange={setFullName}
          autoComplete={AUTOCOMPLETE_NAME}
          error={fieldError(fieldErrors.full_name)}
        />

        <UserRoleSelect value={role} onChange={setRole} />

        <CreatePasswordField
          id={`${fieldId}-password`}
          value={password}
          onChange={setPassword}
          error={fieldError(fieldErrors.password)}
        />

        <UserDialogActions
          onClose={onClose}
          isLoading={status.isLoading}
          label={t("create")}
          loadingLabel={t("creating")}
        />
      </form>
    </UserDialogShell>
  );
}
