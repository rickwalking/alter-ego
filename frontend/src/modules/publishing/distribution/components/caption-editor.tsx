"use client";

interface CaptionEditorProps {
  value: string;
  onChange: (value: string) => void;
  maxChars: number;
  placeholder: string;
  ariaLabel: string;
  helpText?: string;
}

/**
 * Textarea with live character counter. Counter turns red when the
 * value exceeds maxChars — the platform will reject it, so make the
 * problem visible.
 */
export function CaptionEditor({
  value,
  onChange,
  maxChars,
  placeholder,
  ariaLabel,
  helpText,
}: CaptionEditorProps) {
  const count = value.length;
  const over = count > maxChars;

  return (
    <div className="space-y-2">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        rows={10}
        className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 font-mono text-sm focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
      />
      <div className="flex items-center justify-between text-xs">
        {helpText && (
          <p className="text-[var(--color-text-muted)]">{helpText}</p>
        )}
        <p
          className={`ml-auto font-mono ${
            over
              ? "font-semibold text-destructive"
              : "text-[var(--color-text-muted)]"
          }`}
        >
          {count} / {maxChars}
        </p>
      </div>
    </div>
  );
}

export function countHashtags(text: string): number {
  const matches = text.match(/#[\p{L}\p{N}_]+/gu);
  return matches ? matches.length : 0;
}
