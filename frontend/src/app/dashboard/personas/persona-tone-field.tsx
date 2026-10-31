"use client";

import { useTranslations } from "next-intl";
import { TONE_KEYS, type ToneKey } from "@/schemas/persona";

const TONE_STEP = 0.05;
const PERCENT = 100;

/**
 * A 44 px tall native range input with a visible keyboard focus ring; on a
 * phone it takes the full row under its label and value.
 */
const SLIDER_CLASS =
  "order-last col-span-2 h-11 w-full cursor-pointer rounded-md accent-[var(--color-neon-cyan)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep sm:order-none sm:col-span-1";

interface PersonaToneFieldProps {
  tone: Readonly<Record<ToneKey, number>>;
  onChange: (key: ToneKey, value: number) => void;
}

/** The three tone sliders (0–1), each showing and announcing its percentage. */
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
            className="grid grid-cols-[1fr_3rem] items-center gap-x-3 sm:grid-cols-[8rem_1fr_3rem]"
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
              className={SLIDER_CLASS}
            />
            <output
              htmlFor={id}
              data-testid={`${id}-value`}
              className="text-right font-mono text-xs text-text-primary"
              aria-hidden="true"
            >
              {percent}%
            </output>
          </div>
        );
      })}
    </fieldset>
  );
}
