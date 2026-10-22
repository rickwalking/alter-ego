"use client";

import { useTranslations } from "next-intl";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { NeonFormFooter } from "@/components/molecules/neon-form-footer";
import {
  NeonDescriptionField,
  NeonEntityForm,
  NeonNameField,
} from "@/components/molecules/neon-entity-form";
import { NeonLabelledField } from "@/components/molecules/neon-labelled-field";
import { useGuardedForm } from "@/lib/use-guarded-form";
import type { PersonaCreatePayload, PersonaProfile } from "@/modules/persona";
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
  const {
    formRef,
    showErrors,
    saving,
    serverError,
    handleSubmit,
    handleCancel,
    errorOf,
  } = useGuardedForm({ form, onSave, onCancel, t });

  return (
    <NeonEntityForm
      formRef={formRef}
      idPrefix="persona"
      title={persona ? t("editTitle") : t("createTitle")}
      onSubmit={handleSubmit}
    >
      <NeonNameField
        id="persona-name"
        label={t("name")}
        placeholder={t("namePlaceholder")}
        maxLength={PERSONA_NAME_MAX}
        value={form.state.name}
        error={errorOf("name")}
        onChange={form.setName}
      />
      <NeonDescriptionField
        id="persona-description"
        label={t("description")}
        placeholder={t("descriptionPlaceholder")}
        value={form.state.description}
        onChange={(value) => form.setText("description", value)}
      />
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
    </NeonEntityForm>
  );
}
