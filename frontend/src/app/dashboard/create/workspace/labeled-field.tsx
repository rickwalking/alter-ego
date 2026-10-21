import { useId } from "react";
import { TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import { INPUT_FOCUS_CLASS, inputStyle } from "./section-styles";

export interface LabeledFieldProps {
  label: string;
  /** Optional dim hint after the label (e.g. "max 500 chars"). */
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
  /** Render a textarea instead of a single-line input. */
  multiline?: boolean;
  rows?: number;
  /** Bottom margin on the field wrapper (omit for the last field in a section). */
  marginBottom?: string;
}

const counterStyle = {
  display: "block",
  marginTop: "4px",
  fontSize: "11px",
  color: TEXT_DIM,
  textAlign: "right",
  fontVariantNumeric: "tabular-nums",
} as const;

/**
 * Labelled text field used by the create-carousel workspace sections.
 * The topic/audience/brief fields shared identical label + input markup; they
 * now render through this. Supports both single-line input and textarea.
 *
 * the label is tied to the control (`htmlFor`/`id`), the
 * control shows a visible focus ring, and a field with a `maxLength` shows a
 * live `count/max` counter (described-by) instead of silently truncating.
 */
export function LabeledField({
  label,
  hint,
  value,
  onChange,
  placeholder,
  maxLength,
  multiline = false,
  rows = 4,
  marginBottom,
}: Readonly<LabeledFieldProps>): React.ReactElement {
  const id = useId();
  const counterId = `${id}-counter`;
  const controlProps = {
    id,
    value,
    placeholder,
    maxLength,
    className: INPUT_FOCUS_CLASS,
    "aria-describedby": maxLength !== undefined ? counterId : undefined,
  };
  return (
    <div style={marginBottom ? { marginBottom } : undefined}>
      <label
        htmlFor={id}
        style={{
          fontSize: "12px",
          color: TEXT_MUTED,
          marginBottom: "6px",
          display: "block",
        }}
      >
        {label}
        {hint && (
          <>
            {" "}
            <span style={{ color: TEXT_DIM, fontSize: "11px" }}>({hint})</span>
          </>
        )}
      </label>
      {multiline ? (
        <textarea
          {...controlProps}
          onChange={(e) => onChange(e.target.value)}
          rows={rows}
          style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
        />
      ) : (
        <input
          {...controlProps}
          type="text"
          onChange={(e) => onChange(e.target.value)}
          style={inputStyle}
        />
      )}
      {maxLength !== undefined && (
        <span id={counterId} style={counterStyle}>
          {value.length}/{maxLength}
        </span>
      )}
    </div>
  );
}
