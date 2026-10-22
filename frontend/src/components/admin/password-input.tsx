"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { FIELD_INPUT_CLASS } from "./user-dialog-parts";

const INPUT_TYPE_MASKED = "password";
const INPUT_TYPE_VISIBLE = "text";
const AUTOCOMPLETE_NEW_CREDENTIAL = "new-password";
const AUTOCAPITALIZE_OFF = "none";
const INPUT_CLASS = `${FIELD_INPUT_CLASS} pr-11`;
const TOGGLE_CLASS =
  "absolute bottom-0 right-0 top-1 flex w-11 items-center justify-center rounded-md text-gray-500 hover:text-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500";
const ICON_CLASS = "h-4 w-4";

interface PasswordInputProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

/**
 * A new-password input that stays masked until the user presses its labelled
 * show/hide toggle. The toggle is a plain button (never submits the form) and
 * its accessible name says what pressing it will do.
 */
export function PasswordInput({
  id,
  value,
  onChange,
  placeholder,
}: Readonly<PasswordInputProps>) {
  const t = useTranslations("admin");
  const [visible, setVisible] = useState(false);
  const ToggleIcon = visible ? EyeOff : Eye;
  return (
    <div className="relative">
      <input
        id={id}
        type={visible ? INPUT_TYPE_VISIBLE : INPUT_TYPE_MASKED}
        autoComplete={AUTOCOMPLETE_NEW_CREDENTIAL}
        autoCapitalize={AUTOCAPITALIZE_OFF}
        spellCheck={false}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={INPUT_CLASS}
      />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        aria-controls={id}
        aria-label={visible ? t("hidePassword") : t("showPassword")}
        className={TOGGLE_CLASS}
      >
        <ToggleIcon aria-hidden="true" className={ICON_CLASS} />
      </button>
    </div>
  );
}
