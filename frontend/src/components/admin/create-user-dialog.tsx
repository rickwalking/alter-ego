"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

interface CreateUserDialogProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function CreateUserDialog({
  onClose,
  onSuccess,
}: CreateUserDialogProps) {
  const t = useTranslations("admin");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("editor");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setIsLoading(true);

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
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || t("createError"));
      }

      const data = (await response.json()) as { temp_password?: string };

      if (data.temp_password) {
        setSuccess(
          t("createSuccessWithPassword", { password: data.temp_password }),
        );
      } else {
        setSuccess(t("createSuccess"));
      }

      setTimeout(() => {
        onSuccess();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("createError"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center   bg-background/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">
          {t("createUserTitle")}
        </h2>

        {error && (
          <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-4 rounded-md bg-success/10 p-3 text-sm text-success-foreground">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t("emailLabel")}
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t("fullNameLabel")}
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            />
          </div>

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

          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t("passwordLabel")}
              <span className="ml-1 text-xs text-gray-500">
                ({t("passwordOptional")})
              </span>
            </label>
            <input
              type="text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t("passwordPlaceholder")}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            />
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
              {isLoading ? t("creating") : t("create")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
