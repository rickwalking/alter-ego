"use client";

import { useTranslations } from "next-intl";

interface UserActiveFieldProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** Locks the checkbox (the last active admin cannot be deactivated). */
  disabled: boolean;
  /** Id of the text that explains why the checkbox is locked, if it is. */
  describedBy?: string;
}

/** The "Active" checkbox of the edit dialog, at least 44 px tall. */
export function UserActiveField({
  checked,
  onChange,
  disabled,
  describedBy,
}: Readonly<UserActiveFieldProps>) {
  const t = useTranslations("admin");
  return (
    <div className="flex min-h-11 items-center">
      <input
        id="is_active"
        type="checkbox"
        checked={checked}
        disabled={disabled}
        aria-describedby={describedBy}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-5 rounded accent-neon-cyan disabled:opacity-60"
      />
      <label
        htmlFor="is_active"
        className="ml-2 block text-sm text-text-primary"
      >
        {t("activeLabel")}
      </label>
    </div>
  );
}
