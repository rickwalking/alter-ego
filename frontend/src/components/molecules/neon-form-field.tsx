import { type ReactNode } from "react";
import { NeonLabel } from "@/components/atoms/neon-label";
import { NEON_RED, TEXT_DIM } from "@/constants/neon";
import type { NeonFormFieldProps } from "@/schemas/neon-form-field";

export interface NeonFormFieldComponentProps extends NeonFormFieldProps {
  children: ReactNode;
  className?: string;
}

export function NeonFormField({
  label,
  name,
  error,
  hint,
  required,
  children,
  className,
}: NeonFormFieldComponentProps): React.ReactElement {
  return (
    <div className={`space-y-2 ${className ?? ""}`}>
      <NeonLabel htmlFor={name} required={required}>
        {label}
      </NeonLabel>
      {children}
      {hint && !error && (
        <p className="text-xs" style={{ color: TEXT_DIM }}>
          {hint}
        </p>
      )}
      {error && (
        <p className="text-xs" style={{ color: NEON_RED }} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
