import { TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import { inputStyle } from "./section-styles";

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

/**
 * Labelled text field used by the create-carousel workspace sections (AE-0154).
 * The topic/audience/brief fields shared identical label + input markup; they
 * now render through this. Supports both single-line input and textarea.
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
}: LabeledFieldProps): React.ReactElement {
  return (
    <div style={marginBottom ? { marginBottom } : undefined}>
      <label
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
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={rows}
          style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
          placeholder={placeholder}
          maxLength={maxLength}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={inputStyle}
          placeholder={placeholder}
          maxLength={maxLength}
        />
      )}
    </div>
  );
}
