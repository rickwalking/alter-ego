"use client";

import {
  FIELD_ERROR_CLASS,
  FIELD_INPUT_CLASS,
  FIELD_LABEL_CLASS,
} from "./user-dialog-parts";

interface UserFormFieldProps {
  id: string;
  label: string;
  type: "email" | "text";
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  /** The translated validation message; the input is marked invalid when set. */
  error?: string;
}

/**
 * A labelled, required text input of a user form. A validation message shows
 * under it, marks it invalid and describes it, so a screen reader reads the
 * reason with the field.
 */
export function UserFormField({
  id,
  label,
  type,
  value,
  onChange,
  autoComplete,
  error,
}: Readonly<UserFormFieldProps>) {
  const errorId = `${id}-error`;
  return (
    <div>
      <label htmlFor={id} className={FIELD_LABEL_CLASS}>
        {label}
      </label>
      <input
        id={id}
        type={type}
        required
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={error !== undefined}
        aria-describedby={error === undefined ? undefined : errorId}
        className={FIELD_INPUT_CLASS}
      />
      {error !== undefined && (
        <p id={errorId} className={FIELD_ERROR_CLASS}>
          {error}
        </p>
      )}
    </div>
  );
}
