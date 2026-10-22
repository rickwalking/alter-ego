"use client";

import { useState, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";
import { NeonInput } from "@/components/atoms/neon-input";

const ADD_KEY = "Enter";

interface PersonaPhraseListFieldProps {
  id: string;
  label: string;
  hint: string;
  phrases: readonly string[];
  onAdd: (raw: string) => void;
  onRemove: (phrase: string) => void;
}

/** A phrase list edited as chips: Enter (or leaving the field) adds, a chip's button removes. */
export function PersonaPhraseListField({
  id,
  label,
  hint,
  phrases,
  onAdd,
  onRemove,
}: Readonly<PersonaPhraseListFieldProps>): React.ReactElement {
  const t = useTranslations("personas.form");
  const [draft, setDraft] = useState("");

  const commit = (): void => {
    onAdd(draft);
    setDraft("");
  };

  const handleKey = (event: KeyboardEvent<HTMLInputElement>): void => {
    if (event.key !== ADD_KEY) return;
    event.preventDefault();
    commit();
  };

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs text-text-muted">
        {label}
      </label>
      <NeonInput
        id={id}
        value={draft}
        autoComplete="off"
        aria-describedby={`${id}-hint`}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKey}
        onBlur={commit}
      />
      <p id={`${id}-hint`} className="text-[11px] text-text-dim">
        {hint}
      </p>
      {phrases.length > 0 && (
        <ul className="flex flex-wrap gap-1.5 pt-1">
          {phrases.map((phrase) => (
            <li
              key={phrase}
              className="flex items-center gap-1 rounded-full bg-white/5 py-0.5 pl-2 pr-1 text-xs text-text-primary"
            >
              {phrase}
              <button
                type="button"
                onClick={() => onRemove(phrase)}
                className="rounded-full px-1 text-text-muted hover:text-neon-red focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-neon-cyan"
                aria-label={t("removePhrase", { phrase })}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
