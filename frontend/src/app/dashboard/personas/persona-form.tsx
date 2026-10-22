"use client";

import { useTranslations } from "next-intl";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { NeonFormFooter } from "@/components/molecules/neon-form-footer";
import {
  NeonLabelledField,
  invalidProps,
} from "@/components/molecules/neon-labelled-field";
import { useFormSubmit } from "@/lib/use-form-submit";
import type { PersonaCreatePayload, PersonaProfile } from "@/modules/persona";
import { useUnsavedChangesGuard } from "@/modules/publishing";
import { PERSONA_NAME_MAX } from "@/schemas/persona";
import type { PhraseListKey, StyleTextKey } from "./persona-form-model";
import { PersonaPhraseListField } from "./persona-phrase-list-field";
import { PersonaSamplesField } from "./persona-samples-field";
import { PersonaToneField } from "./persona-tone-field";
import { usePersonaForm, type UsePersonaFormResult } from "./use-persona-form";

/** The style text fields, in form order, with their label key. */
const STYLE_FIELDS: readonly [StyleTextKey, string][] = [
  ["sentence_structure_preferences", "sentenceStructure"],
  ["paragraph_style", "paragraphStyle"],
  ["opinion_expression", "opinionExpression"],
];

/** The phrase lists, in form order, with their label and hint keys. */
const PHRASE_FIELDS: readonly [PhraseListKey, string][] = [
  ["preferred_phrases", "preferred"],
  ["forbidden_phrases", "forbidden"],
];

export interface PersonaFormProps {
  /** The persona being edited; omitted when creating one. */
  persona?: PersonaProfile;
  /** Persist the payload; a rejection keeps the form open with the reason. */
  onSave: (payload: PersonaCreatePayload) => Promise<void>;
  /** Leave the form without saving. */
  onCancel: () => void;
}

function VoiceFields({
  form,
}: Readonly<{ form: UsePersonaFormResult }>): React.ReactElement {
  const t = useTranslations("personas.form");
  return (
    <>
      <PersonaToneField tone={form.state.tone} onChange={form.setTone} />
      {STYLE_FIELDS.map(([key, label]) => (
        <NeonLabelledField key={key} id={`persona-${key}`} label={t(label)}>
          <NeonTextarea
            id={`persona-${key}`}
            value={form.state[key]}
            onChange={(e) => form.setText(key, e.target.value)}
          />
        </NeonLabelledField>
      ))}
      {PHRASE_FIELDS.map(([key, label]) => (
        <PersonaPhraseListField
          key={key}
          id={`persona-${key}`}
          label={t(label)}
          hint={t(`${label}Hint`)}
          phrases={form.state[key]}
          onAdd={(raw) => form.addToList(key, raw)}
          onRemove={(phrase) => form.removeFromList(key, phrase)}
        />
      ))}
    </>
  );
}

/** The persona create/edit form: identity, voice, phrases, samples and save. */
export function PersonaForm({
  persona,
  onSave,
  onCancel,
}: Readonly<PersonaFormProps>): React.ReactElement {
  const t = useTranslations("personas.form");
  const form = usePersonaForm(persona);
  const { confirmLeave } = useUnsavedChangesGuard(
    form.dirty,
    t("unsavedConfirm"),
  );
  const {
    formRef,
    showErrors,
    saving,
    serverError,
    handleSubmit,
    handleCancel,
  } = useFormSubmit({
    isValid: form.isValid,
    toPayload: form.toPayload,
    onSave,
    onCancel,
    confirmLeave,
    saveFallback: t("errors.save"),
  });
  const errorOf = (path: string): string | undefined => {
    const key = showErrors ? form.errors[path] : undefined;
    return key ? t(key) : undefined;
  };

  return (
    <form
      ref={formRef}
      noValidate
      aria-labelledby="persona-form-title"
      className="flex max-w-3xl flex-col gap-5"
      onSubmit={(e) => void handleSubmit(e)}
    >
      <h2 id="persona-form-title" className="text-lg font-bold">
        {persona ? t("editTitle") : t("createTitle")}
      </h2>
      <NeonLabelledField
        id="persona-name"
        label={t("name")}
        error={errorOf("name")}
      >
        <NeonInput
          id="persona-name"
          value={form.state.name}
          maxLength={PERSONA_NAME_MAX}
          autoComplete="off"
          placeholder={t("namePlaceholder")}
          {...invalidProps("persona-name", errorOf("name"))}
          onChange={(e) => form.setName(e.target.value)}
        />
      </NeonLabelledField>
      <NeonLabelledField id="persona-description" label={t("description")}>
        <NeonTextarea
          id="persona-description"
          value={form.state.description}
          placeholder={t("descriptionPlaceholder")}
          onChange={(e) => form.setText("description", e.target.value)}
        />
      </NeonLabelledField>
      <PersonaPhraseListField
        id="persona-expertise_areas"
        label={t("expertise")}
        hint={t("expertiseHint")}
        phrases={form.state.expertise_areas}
        onAdd={(raw) => form.addToList("expertise_areas", raw)}
        onRemove={(phrase) => form.removeFromList("expertise_areas", phrase)}
      />
      <VoiceFields form={form} />
      <PersonaSamplesField
        samples={form.state.writing_samples}
        addedSampleId={form.addedSampleId}
        errorOf={(index) => errorOf(`writing_samples.${index}`)}
        onAdd={form.addSample}
        onChange={form.setSample}
        onRemove={form.removeSample}
      />
      <NeonFormFooter
        serverError={serverError}
        invalidMessage={showErrors && !form.isValid ? t("fixErrors") : null}
        cancelLabel={t("cancel")}
        submitLabel={persona ? t("save") : t("create")}
        saving={saving}
        onCancel={handleCancel}
      />
    </form>
  );
}
