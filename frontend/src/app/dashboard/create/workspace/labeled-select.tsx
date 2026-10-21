import { TEXT_MUTED } from "@/constants/neon";
import { INPUT_FOCUS_CLASS, inputStyle } from "./section-styles";

export interface LabeledSelectOption {
  value: string;
  label: string;
}

export interface LabeledSelectProps {
  label: string;
  value: string;
  options: readonly LabeledSelectOption[];
  onChange: (value: string) => void;
  /** Bottom margin on the field wrapper (omit for the last field). */
  marginBottom?: string;
}

/** Labelled `<select>` for the create-carousel sections (AE-0373). */
export function LabeledSelect({
  label,
  value,
  options,
  onChange,
  marginBottom,
}: Readonly<LabeledSelectProps>): React.ReactElement {
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
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={INPUT_FOCUS_CLASS}
          style={{ ...inputStyle, marginTop: "6px" }}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
