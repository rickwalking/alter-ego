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

interface DeleteUserDialogProps {
  user: UserItem;
  onClose: () => void;
  onSuccess: () => void;
}

export function DeleteUserDialog({
  user,
  onClose,
  onSuccess,
}: DeleteUserDialogProps) {
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
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || t("deleteError"));
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
    <div className="fixed inset-0 z-50 flex items-center justify-center   bg-background/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">
          {t("deleteUserTitle")}
        </h2>
        <p className="mt-2 text-sm text-gray-500">
          {t("deleteUserDescription", { email: user.email })}
        </p>

        {error && (
          <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="mt-6 flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {t("cancel")}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isLoading}
            className="rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
          >
            {isLoading ? t("deleting") : t("delete")}
          </button>
        </div>
      </div>
    </div>
  );
}
