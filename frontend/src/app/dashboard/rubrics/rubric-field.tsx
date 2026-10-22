import type { ReactNode } from "react";
import { NEON_RED } from "@/constants/neon";

const ERROR_ID_SUFFIX = "-error";

/** The id of a field's error text, for the control's `aria-describedby`. */
export function fieldErrorId(fieldId: string): string {
  return `${fieldId}${ERROR_ID_SUFFIX}`;
}

/** The accessibility props of a control whose field may show an error. */
export function invalidProps(
  fieldId: string,
  error: string | undefined,
): { "aria-invalid": boolean; "aria-describedby": string | undefined } {
  return {
    "aria-invalid": error !== undefined,
    "aria-describedby": error ? fieldErrorId(fieldId) : undefined,
  };
}

interface RubricFieldProps {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  className?: string;
  children: ReactNode;
}

/** A labelled form control with its hint and (translated) error text. */
export function RubricField({
  id,
  label,
  error,
  hint,
  className,
  children,
}: Readonly<RubricFieldProps>): React.ReactElement {
  return (
    <div className={`flex flex-col gap-1 ${className ?? ""}`}>
      <label htmlFor={id} className="text-xs text-text-muted">
        {label}
      </label>
      {children}
      {hint && <p className="text-[11px] text-text-dim">{hint}</p>}
      {error && (
        <p
          id={fieldErrorId(id)}
          className="text-xs"
          style={{ color: NEON_RED }}
        >
          {error}
        </p>
      )}
    </div>
  );
}
