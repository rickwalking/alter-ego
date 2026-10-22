"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { responseErrorDetail } from "@/lib/response-error";
import {
  UserDialogActions,
  UserDialogShell,
  type UserDialogProps,
} from "./user-dialog-parts";

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
      const response = await fetch(`/api/admin/users/${user.id}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(
          (await responseErrorDetail(response)) ?? t("deleteError"),
        );
      }

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("deleteError"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <UserDialogShell
      title={t("deleteUserTitle")}
      subtitle={
        <p className="mt-2 text-sm text-gray-500">
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
