"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { responseErrorDetail } from "@/lib/response-error";
import {
  UserDialogActions,
  UserDialogShell,
  UserRoleSelect,
  type UserDialogProps,
} from "./user-dialog-parts";

export function EditUserDialog({
  user,
  onClose,
  onSuccess,
}: Readonly<UserDialogProps>) {
  const t = useTranslations("admin");
  const [role, setRole] = useState(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.SubmitEvent) => {
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
        throw new Error(
          (await responseErrorDetail(response)) ?? t("updateError"),
        );
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
    <UserDialogShell
      title={t("editUserTitle")}
      subtitle={<p className="text-sm text-gray-500">{user.email}</p>}
      error={error}
    >
      <form
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="mt-4 space-y-4"
      >
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
          isLoading={isLoading}
          label={t("save")}
          loadingLabel={t("saving")}
        />
      </form>
    </UserDialogShell>
  );
}
