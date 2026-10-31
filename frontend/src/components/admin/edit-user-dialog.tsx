"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { HTTP_STATUS } from "@/constants/api";
import { responseErrorDetail } from "@/lib/response-error";
import {
  buildUserUpdatePayload,
  isValidFullName,
  type UserUpdateDraft,
} from "@/lib/user-update";
import { cn } from "@/lib/utils";
import {
  FIELD_INPUT_CLASS,
  FIELD_LABEL_CLASS,
  UserDialogActions,
  UserDialogShell,
  useDialogStatus,
  UserRoleSelect,
  type UserDialogProps,
  type UserItem,
} from "./user-dialog-parts";

interface UpdateFailureMessages {
  invalidName: string;
  fallback: string;
}

/**
 * The error text for a failed update: the API's own message when it sends one,
 * the name-validation message for a 422 validation list, else the fallback.
 */
async function updateFailureMessage(
  response: Response,
  messages: UpdateFailureMessages,
): Promise<string> {
  const detail = await responseErrorDetail(response);
  if (detail !== undefined) {
    return detail;
  }
  return response.status === HTTP_STATUS.UNPROCESSABLE_ENTITY
    ? messages.invalidName
    : messages.fallback;
}

/** PATCH the draft for `user`; throws with the error text when it fails. */
async function sendUserUpdate(
  user: UserItem,
  draft: UserUpdateDraft,
  messages: UpdateFailureMessages,
): Promise<void> {
  const response = await fetch(`/api/admin/users/${user.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(buildUserUpdatePayload(user.full_name, draft)),
  });
  if (!response.ok) {
    throw new Error(await updateFailureMessage(response, messages));
  }
}

interface FullNameFieldProps {
  value: string;
  onChange: (value: string) => void;
}

/** The labelled, editable full-name input of the edit dialog. */
function FullNameField({ value, onChange }: Readonly<FullNameFieldProps>) {
  const t = useTranslations("admin");
  const inputId = useId();
  return (
    <div>
      <label htmlFor={inputId} className={FIELD_LABEL_CLASS}>
        {t("fullNameLabel")}
      </label>
      <input
        id={inputId}
        type="text"
        autoComplete="name"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(FIELD_INPUT_CLASS, "focus-visible:ring-2")}
      />
    </div>
  );
}

export function EditUserDialog({
  user,
  onClose,
  onSuccess,
}: Readonly<UserDialogProps>) {
  const t = useTranslations("admin");
  const [role, setRole] = useState(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [fullName, setFullName] = useState(user.full_name);
  const status = useDialogStatus();

  const handleSubmit = async (e: React.SubmitEvent) => {
    e.preventDefault();
    if (!isValidFullName(fullName)) {
      status.setError(t("nameInvalid"));
      return;
    }
    status.begin();
    try {
      await sendUserUpdate(
        user,
        { role, isActive, fullName },
        { invalidName: t("nameInvalid"), fallback: t("updateError") },
      );
      onSuccess();
      onClose();
    } catch (err) {
      status.setError(err instanceof Error ? err.message : t("updateError"));
    } finally {
      status.finish();
    }
  };

  return (
    <UserDialogShell
      title={t("editUserTitle")}
      subtitle={<p className="text-sm text-gray-500">{user.email}</p>}
      error={status.error}
    >
      <form
        noValidate
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="mt-4 space-y-4"
      >
        <FullNameField value={fullName} onChange={setFullName} />

        <UserRoleSelect value={role} onChange={setRole} />

        <div className="flex items-center">
          <input
            id="is_active"
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary-500"
          />
          <label
            htmlFor="is_active"
            className="ml-2 block text-sm text-gray-900"
          >
            {t("activeLabel")}
          </label>
        </div>

        <UserDialogActions
          onClose={onClose}
          isLoading={status.isLoading}
          label={t("save")}
          loadingLabel={t("saving")}
        />
      </form>
    </UserDialogShell>
  );
}
