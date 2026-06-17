"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface ChangePasswordDialogProps {
  user: UserItem;
  onClose: () => void;
  onSuccess: () => void;
}

export function ChangePasswordDialog({
  user,
  onClose,
  onSuccess,
}: ChangePasswordDialogProps) {
  const t = useTranslations("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setIsLoading(true);

    try {
      const response = await fetch(
        `/api/admin/users/${user.id}/reset-password`,
        {
          method: "POST",
          credentials: "include",
        },
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || t("resetError"));
      }

      const data = (await response.json()) as { temp_password: string };
      setPassword(data.temp_password);
      setSuccess(t("resetSuccess"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("resetError"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center   bg-background/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">
          {t("resetPasswordTitle")}
        </h2>
        <p className="text-sm text-gray-500">{user.email}</p>

        {error && (
          <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-4 rounded-md bg-success/10 p-3 text-sm text-success-foreground">
            {success}
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
          </div>
        )}

        {!success && (
          <form
            onSubmit={(e) => {
              void handleSubmit(e);
            }}
            className="mt-4"
          >
            <p className="text-sm text-gray-600">
              {t("resetPasswordDescription")}
            </p>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {t("cancel")}
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary-600 disabled:opacity-50"
              >
                {isLoading ? t("resetting") : t("reset")}
              </button>
            </div>
          </form>
        )}

        {success && (
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={() => {
                onSuccess();
                onClose();
              }}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary-600"
            >
              {t("done")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
