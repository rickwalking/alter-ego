"use client";

import { type ReactNode, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonModal } from "@/components/molecules/neon-modal";
import { TOUCH_TARGET_CLASS } from "@/constants/admin-users";
import { cn } from "@/lib/utils";

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

export const FIELD_LABEL_CLASS = "block text-sm font-medium text-text-primary";
export const FIELD_INPUT_CLASS =
  "mt-1 block h-11 w-full rounded-md border border-[var(--color-neon-input-border)] bg-[var(--color-neon-input-bg)] px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-neon-cyan focus:outline-none focus:ring-neon-cyan aria-[invalid=true]:border-neon-red";
/** Muted secondary text of a dialog (subtitle, description, field hint). */
export const DIALOG_MUTED_TEXT_CLASS = "text-sm text-text-muted";
/** A field-level validation message under its input. */
export const FIELD_ERROR_CLASS = "mt-1 text-sm text-neon-red";
/** Dialog buttons: the neon button, at least 44 px tall to tap. */
export const DIALOG_BUTTON_CLASS = TOUCH_TARGET_CLASS;

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

interface UserDialogShellProps {
  title: string;
  /** Escape, the backdrop and the Cancel button all call it. */
  onClose: () => void;
  subtitle?: ReactNode;
  error: string;
  /** Id of the error banner, so a field can point `aria-describedby` at it. */
  errorId?: string;
  success?: ReactNode;
  /** `alertdialog` for the destructive confirmation (delete). */
  role?: "dialog" | "alertdialog";
  /** Id of the text that describes the dialog. */
  descriptionId?: string;
  children: ReactNode;
}

/**
 * The modal frame of every admin user dialog, built on the dashboard's
 * NeonModal: labelled by its title, focus trapped inside, Escape and the
 * backdrop close it, and focus returns to the button that opened it.
 */
export function UserDialogShell({
  title,
  onClose,
  subtitle,
  error,
  errorId,
  success,
  role,
  descriptionId,
  children,
}: Readonly<UserDialogShellProps>) {
  const t = useTranslations("admin");
  return (
    <NeonModal
      open
      onClose={onClose}
      title={title}
      role={role}
      closeLabel={t("closeDialog")}
      describedBy={descriptionId}
      footer={false}
    >
      {subtitle}

      {error && (
        <div
          id={errorId}
          role="alert"
          className="mt-4 rounded-md border border-neon-red/30 bg-neon-red/10 p-3 text-sm text-text-primary"
        >
          {error}
        </div>
      )}
      {success && (
        <div
          role="status"
          className="mt-4 rounded-md border border-neon-green/30 bg-neon-green/10 p-3 text-sm text-text-primary"
        >
          {success}
        </div>
      )}

      {children}
    </NeonModal>
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
    <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
      <NeonButton
        variant="ghost"
        onClick={onClose}
        className={DIALOG_BUTTON_CLASS}
      >
        {t("cancel")}
      </NeonButton>
      <NeonButton
        type={destructive ? "button" : "submit"}
        variant={destructive ? "danger" : "primary"}
        onClick={onConfirm}
        disabled={isLoading}
        className={DIALOG_BUTTON_CLASS}
      >
        {isLoading ? loadingLabel : label}
      </NeonButton>
    </div>
  );
}

interface UserRoleSelectProps {
  value: string;
  onChange: (role: string) => void;
  /** Locks the select (the last active admin cannot be demoted). */
  disabled?: boolean;
  /** Id of the text that explains the select, e.g. why it is locked. */
  describedBy?: string;
}

export function UserRoleSelect({
  value,
  onChange,
  disabled = false,
  describedBy,
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
        disabled={disabled}
        aria-describedby={describedBy}
        className={cn(FIELD_INPUT_CLASS, "disabled:opacity-60")}
      >
        <option value="editor">{t("editorRole")}</option>
        <option value="admin">{t("adminRole")}</option>
      </select>
    </div>
  );
}
