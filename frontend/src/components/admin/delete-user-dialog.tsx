"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { adminErrorKey } from "@/lib/admin-user-errors";
import { responseErrorBody } from "@/lib/response-error";
import {
  DIALOG_MUTED_TEXT_CLASS,
  UserDialogActions,
  UserDialogShell,
  type UserDialogProps,
} from "./user-dialog-parts";

const DELETE_ERROR_KEY = "deleteError";
const DIALOG_ROLE_ALERT = "alertdialog";

/** DELETE the user; the message key of a failure, else undefined. */
async function requestDelete(userId: string): Promise<string | undefined> {
  const response = await fetch(`/api/admin/users/${userId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (response.ok) {
    return undefined;
  }
  const body = await responseErrorBody(response);
  return adminErrorKey(response.status, body) ?? DELETE_ERROR_KEY;
}

export function DeleteUserDialog({
  user,
  onClose,
  onSuccess,
}: Readonly<UserDialogProps>) {
  const t = useTranslations("admin");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleDelete = async () => {
    setError("");
    setIsLoading(true);
    try {
      const failureKey = await requestDelete(user.id);
      if (failureKey !== undefined) {
        setError(t(failureKey));
        return;
      }
      onSuccess();
      onClose();
    } catch {
      setError(t(DELETE_ERROR_KEY));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <UserDialogShell
      title={t("deleteUserTitle")}
      onClose={onClose}
      role={DIALOG_ROLE_ALERT}
      subtitle={
        <p className={DIALOG_MUTED_TEXT_CLASS}>
          {t("deleteUserDescription", { email: user.email })}
        </p>
      }
      error={error}
    >
      <UserDialogActions
        onClose={onClose}
        isLoading={isLoading}
        label={t("delete")}
        loadingLabel={t("deleting")}
        onConfirm={() => {
          void handleDelete();
        }}
      />
    </UserDialogShell>
  );
}
