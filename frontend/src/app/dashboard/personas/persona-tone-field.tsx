"use client";

import { useTranslations } from "next-intl";
import { TONE_KEYS, type ToneKey } from "@/schemas/persona";

const TONE_STEP = 0.05;
const PERCENT = 100;

interface PersonaToneFieldProps {
  tone: Readonly<Record<ToneKey, number>>;
  onChange: (key: ToneKey, value: number) => void;
}

/** The three tone sliders (0–1), each announcing its value as a percentage. */
export function PersonaToneField({
  tone,
  onChange,
}: Readonly<PersonaToneFieldProps>): React.ReactElement {
  const t = useTranslations("personas");
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-1 text-xs text-text-muted">{t("form.tone")}</legend>
      {TONE_KEYS.map((key) => {
        const id = `persona-tone-${key}`;
        const percent = Math.round(tone[key] * PERCENT);
        return (
          <div
            key={key}
            className="grid grid-cols-[8rem_1fr_3rem] items-center gap-3"
          >
            <label htmlFor={id} className="text-sm">
              {t(`tone.${key}`)}
            </label>
            <input
              id={id}
              type="range"
              min={0}
              max={1}
              step={TONE_STEP}
              value={tone[key]}
              aria-valuetext={`${percent}%`}
              onChange={(e) => onChange(key, Number(e.target.value))}
              className="accent-[var(--color-neon-cyan)]"
            />
            <span
              className="text-right font-mono text-xs text-text-muted"
              aria-hidden="true"
            >
              {percent}%
            </span>
          </div>
        );
      })}
    </fieldset>
  );
}
