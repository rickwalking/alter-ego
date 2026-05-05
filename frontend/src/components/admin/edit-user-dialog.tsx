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

interface EditUserDialogProps {
  user: UserItem;
  onClose: () => void;
  onSuccess: () => void;
}

export function EditUserDialog({
  user,
  onClose,
  onSuccess,
}: EditUserDialogProps) {
  const t = useTranslations("admin");
  const [role, setRole] = useState(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await fetch(`/api/admin/users/${user.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ role, is_active: isActive }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || t("updateError"));
      }

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("updateError"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center   bg-background/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">
          {t("editUserTitle")}
        </h2>
        <p className="text-sm text-gray-500">{user.email}</p>

        {error && (
          <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t("roleLabel")}
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            >
              <option value="editor">{t("editorRole")}</option>
              <option value="admin">{t("adminRole")}</option>
            </select>
          </div>

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
              {isLoading ? t("saving") : t("save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
