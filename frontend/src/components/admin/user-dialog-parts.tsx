"use client";

import { type ReactNode, useId, useState } from "react";
import { useTranslations } from "next-intl";

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface UserDialogProps {
  user: UserItem;
  onClose: () => void;
  onSuccess: () => void;
}

export const FIELD_LABEL_CLASS = "block text-sm font-medium text-gray-700";
export const FIELD_INPUT_CLASS =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500";
export interface DialogStatus {
  error: string;
  success: string;
  isLoading: boolean;
  setError: (message: string) => void;
  setSuccess: (message: string) => void;
  begin: () => void;
  finish: () => void;
}

export function useDialogStatus(): DialogStatus {
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  return {
    error,
    success,
    isLoading,
    setError,
    setSuccess,
    begin: () => {
      setError("");
      setSuccess("");
      setIsLoading(true);
    },
    finish: () => setIsLoading(false),
  };
}

const CANCEL_BUTTON_CLASS =
  "rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50";
const PRIMARY_BUTTON_CLASS =
  "rounded-md bg-primary-700 px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary-800 disabled:opacity-50";
const DESTRUCTIVE_BUTTON_CLASS =
  "rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50";

interface UserDialogShellProps {
  title: string;
  subtitle?: ReactNode;
  error: string;
  success?: ReactNode;
  children: ReactNode;
}

export function UserDialogShell({
  title,
  subtitle,
  error,
  success,
  children,
}: Readonly<UserDialogShellProps>) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center   bg-background/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        {subtitle}

        {error && (
          <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-red-800">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-4 rounded-md bg-success/10 p-3 text-sm text-success-foreground">
            {success}
          </div>
        )}

        {children}
      </div>
    </div>
  );
}

interface UserDialogActionsProps {
  onClose: () => void;
  isLoading: boolean;
  label: string;
  loadingLabel: string;
  onConfirm?: () => void;
}

export function UserDialogActions({
  onClose,
  isLoading,
  label,
  loadingLabel,
  onConfirm,
}: Readonly<UserDialogActionsProps>) {
  const t = useTranslations("admin");
  const destructive = onConfirm !== undefined;
  return (
    <div className="mt-6 flex justify-end space-x-3">
      <button type="button" onClick={onClose} className={CANCEL_BUTTON_CLASS}>
        {t("cancel")}
      </button>
      <button
        type={destructive ? "button" : "submit"}
        onClick={onConfirm}
        disabled={isLoading}
        className={
          destructive ? DESTRUCTIVE_BUTTON_CLASS : PRIMARY_BUTTON_CLASS
        }
      >
        {isLoading ? loadingLabel : label}
      </button>
    </div>
  );
}

interface UserRoleSelectProps {
  value: string;
  onChange: (role: string) => void;
}

export function UserRoleSelect({
  value,
  onChange,
}: Readonly<UserRoleSelectProps>) {
  const t = useTranslations("admin");
  const selectId = useId();
  return (
    <div>
      <label htmlFor={selectId} className={FIELD_LABEL_CLASS}>
        {t("roleLabel")}
      </label>
      <select
        id={selectId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={FIELD_INPUT_CLASS}
      >
        <option value="editor">{t("editorRole")}</option>
        <option value="admin">{t("adminRole")}</option>
      </select>
    </div>
  );
}
