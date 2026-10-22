"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { responseErrorDetail } from "@/lib/response-error";
import { PasswordInput } from "./password-input";
import {
  FIELD_INPUT_CLASS,
  FIELD_LABEL_CLASS,
  UserDialogActions,
  UserDialogShell,
  useDialogStatus,
  UserRoleSelect,
} from "./user-dialog-parts";

interface CreateUserDialogProps {
  onClose: () => void;
  onSuccess: () => void;
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
  const status = useDialogStatus();

  const handleSubmit = async (e: React.SubmitEvent) => {
    e.preventDefault();
    status.begin();

    const payload: Record<string, string> = {
      email,
      full_name: fullName,
      role,
    };
    if (password) {
      payload.password = password;
    }

    try {
      const response = await fetch("/api/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(
          (await responseErrorDetail(response)) ?? t("createError"),
        );
      }

      const data = (await response.json()) as { temp_password?: string };

      if (data.temp_password) {
        status.setSuccess(
          t("createSuccessWithPassword", { password: data.temp_password }),
        );
      } else {
        status.setSuccess(t("createSuccess"));
      }

      setTimeout(() => {
        onSuccess();
      }, 2000);
    } catch (err) {
      status.setError(err instanceof Error ? err.message : t("createError"));
    } finally {
      status.finish();
    }
  };

  return (
    <UserDialogShell
      title={t("createUserTitle")}
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
        <div>
          <label htmlFor={`${fieldId}-email`} className={FIELD_LABEL_CLASS}>
            {t("emailLabel")}
          </label>
          <input
            id={`${fieldId}-email`}
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={FIELD_INPUT_CLASS}
          />
        </div>

        <div>
          <label htmlFor={`${fieldId}-full-name`} className={FIELD_LABEL_CLASS}>
            {t("fullNameLabel")}
          </label>
          <input
            id={`${fieldId}-full-name`}
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className={FIELD_INPUT_CLASS}
          />
        </div>

        <UserRoleSelect value={role} onChange={setRole} />

        <div>
          <label htmlFor={`${fieldId}-password`} className={FIELD_LABEL_CLASS}>
            {t("passwordLabel")}
            <span className="ml-1 text-xs text-gray-500">
              ({t("passwordOptional")})
            </span>
          </label>
          <PasswordInput
            id={`${fieldId}-password`}
            value={password}
            onChange={setPassword}
            placeholder={t("passwordPlaceholder")}
          />
        </div>

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
