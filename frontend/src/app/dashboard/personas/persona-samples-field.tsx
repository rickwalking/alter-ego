"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  NeonLabelledField,
  invalidProps,
} from "@/components/molecules/neon-labelled-field";
import type { SampleDraft } from "./persona-form-model";

interface SampleRowProps {
  sample: SampleDraft;
  number: number;
  error?: string;
  focusOnMount: boolean;
  onChange: (text: string) => void;
  onRemove: () => void;
}

function SampleRow({
  sample,
  number,
  error,
  focusOnMount,
  onChange,
  onRemove,
}: Readonly<SampleRowProps>): React.ReactElement {
  const t = useTranslations("personas.form");
  const ref = useRef<HTMLTextAreaElement>(null);
  const id = `persona-sample-${sample.id}`;

  useEffect(() => {
    if (focusOnMount) ref.current?.focus();
  }, [focusOnMount]);

  return (
    <div className="flex items-start gap-2">
      <NeonLabelledField
        id={id}
        label={t("sample", { number })}
        error={error}
        className="flex-1"
      >
        <NeonTextarea
          ref={ref}
          id={id}
          value={sample.text}
          {...invalidProps(id, error)}
          onChange={(e) => onChange(e.target.value)}
        />
      </NeonLabelledField>
      <NeonButton
        variant="ghost"
        size="sm"
        className="mt-5"
        aria-label={t("removeSample", { number })}
        onClick={onRemove}
      >
        ✕
      </NeonButton>
    </div>
  );
}

interface PersonaSamplesFieldProps {
  samples: readonly SampleDraft[];
  addedSampleId: string | null;
  errorOf: (index: number) => string | undefined;
  onAdd: () => void;
  onChange: (id: string, text: string) => void;
  onRemove: (id: string) => void;
}

/** The writing samples of a persona: one text area each, plus add/remove. */
export function PersonaSamplesField({
  samples,
  addedSampleId,
  errorOf,
  onAdd,
  onChange,
  onRemove,
}: Readonly<PersonaSamplesFieldProps>): React.ReactElement {
  const t = useTranslations("personas.form");
  return (
    <section
      aria-labelledby="persona-samples-title"
      className="flex flex-col gap-3"
    >
      <h3 id="persona-samples-title" className="text-sm font-semibold">
        {t("samples")}
      </h3>
      <p className="text-xs text-text-muted">{t("samplesHint")}</p>
      {samples.map((sample, index) => (
        <SampleRow
          key={sample.id}
          sample={sample}
          number={index + 1}
          error={errorOf(index)}
          focusOnMount={sample.id === addedSampleId}
          onChange={(text) => onChange(sample.id, text)}
          onRemove={() => onRemove(sample.id)}
        />
      ))}
      <div>
        <NeonButton variant="secondary" size="sm" onClick={onAdd}>
          {t("addSample")}
        </NeonButton>
      </div>
    </section>
  );
}
