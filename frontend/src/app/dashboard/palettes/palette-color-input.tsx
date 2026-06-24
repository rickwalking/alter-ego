"use client";

import { NeonInput } from "@/components/atoms/neon-input";
import { cn } from "@/lib/utils";

interface PaletteColorInputProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  invalid: boolean;
  errorText: string;
}

const HEX_FALLBACK = "#000000";

/** A single colour field: a native swatch picker bound to a hex text input. */
export function PaletteColorInput({
  id,
  label,
  value,
  onChange,
  invalid,
  errorText,
}: PaletteColorInputProps): React.ReactElement {
  const pickerValue = /^#[0-9a-fA-F]{6}$/.test(value) ? value : HEX_FALLBACK;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs text-text-muted">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={label}
          value={pickerValue}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 w-10 shrink-0 cursor-pointer rounded-md border border-white/10 bg-transparent p-1"
        />
        <NeonInput
          id={id}
          value={value}
          spellCheck={false}
          autoComplete="off"
          placeholder="#22d3ee"
          aria-invalid={invalid}
          onChange={(e) => onChange(e.target.value)}
          className={cn("font-mono", invalid && "border-neon-red")}
        />
      </div>
      {invalid && (
        <p role="alert" className="text-[11px] text-neon-red">
          {errorText}
        </p>
      )}
    </div>
  );
}
