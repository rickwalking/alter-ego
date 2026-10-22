"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { responseErrorDetail } from "@/lib/response-error";
import {
  UserDialogActions,
  UserDialogShell,
  useDialogStatus,
  type UserDialogProps,
} from "./user-dialog-parts";

export function ChangePasswordDialog({
  user,
  onClose,
  onSuccess,
}: Readonly<UserDialogProps>) {
  const t = useTranslations("admin");
  const [password, setPassword] = useState("");
  const status = useDialogStatus();

  const handleSubmit = async (e: React.SubmitEvent) => {
    e.preventDefault();
    status.begin();

    try {
      const response = await fetch(
        `/api/admin/users/${user.id}/reset-password`,
        {
          method: "POST",
          credentials: "include",
        },
      );

      if (!response.ok) {
        throw new Error(
          (await responseErrorDetail(response)) ?? t("resetError"),
        );
      }

      const data = (await response.json()) as { temp_password: string };
      setPassword(data.temp_password);
      status.setSuccess(t("resetSuccess"));
    } catch (err) {
      status.setError(err instanceof Error ? err.message : t("resetError"));
    } finally {
      status.finish();
    }
  };

  return (
    <UserDialogShell
      title={t("resetPasswordTitle")}
      subtitle={<p className="text-sm text-gray-500">{user.email}</p>}
      error={status.error}
      success={
        status.success ? (
          <>
            {status.success}
            <div className="mt-2 flex items-center space-x-2">
              <code className="rounded bg-gray-100 px-2 py-1 text-sm font-mono">
                {password}
              </code>
              <button
                onClick={() => {
                  void navigator.clipboard.writeText(password);
                }}
                className="text-xs text-primary hover:text-primary-900"
              >
                {t("copy")}
              </button>
            </div>
          </>
        ) : undefined
      }
    >
      {!status.success && (
        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="mt-4"
        >
          <p className="text-sm text-gray-600">
            {t("resetPasswordDescription")}
          </p>
          <UserDialogActions
            onClose={onClose}
            isLoading={status.isLoading}
            label={t("reset")}
            loadingLabel={t("resetting")}
          />
        </form>
      )}

      {status.success && (
        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={() => {
              onSuccess();
              onClose();
            }}
            className="rounded-md bg-primary-700 px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary-800"
          >
            {t("done")}
          </button>
        </div>
      )}
    </UserDialogShell>
  );
}
