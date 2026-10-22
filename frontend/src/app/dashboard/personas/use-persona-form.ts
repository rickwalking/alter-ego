"use client";

import { useMemo, useState } from "react";
import type { PersonaCreatePayload, PersonaProfile } from "@/modules/persona";
import type { ToneKey } from "@/schemas/persona";
import {
  addPhrase,
  initialPersonaFormState,
  newSample,
  toPersonaPayload,
  validatePersonaForm,
  type PersonaFormErrors,
  type PersonaFormState,
  type PhraseListKey,
  type StyleTextKey,
} from "./persona-form-model";

export interface UsePersonaFormResult {
  state: PersonaFormState;
  errors: PersonaFormErrors;
  isValid: boolean;
  /** True once the values differ from the ones the form opened with. */
  dirty: boolean;
  /** The id of the sample added last (its text area takes focus). */
  addedSampleId: string | null;
  setName: (value: string) => void;
  setText: (key: StyleTextKey, value: string) => void;
  setTone: (key: ToneKey, value: number) => void;
  addToList: (key: PhraseListKey, raw: string) => void;
  removeFromList: (key: PhraseListKey, phrase: string) => void;
  addSample: () => void;
  setSample: (id: string, text: string) => void;
  removeSample: (id: string) => void;
  toPayload: () => PersonaCreatePayload;
}

type SetState = React.Dispatch<React.SetStateAction<PersonaFormState>>;

function sampleActions(
  setState: SetState,
  setAddedSampleId: (id: string) => void,
): Pick<UsePersonaFormResult, "addSample" | "setSample" | "removeSample"> {
  return {
    addSample: () => {
      const sample = newSample();
      setAddedSampleId(sample.id);
      setState((prev) => ({
        ...prev,
        writing_samples: [...prev.writing_samples, sample],
      }));
    },
    setSample: (id, text) =>
      setState((prev) => ({
        ...prev,
        writing_samples: prev.writing_samples.map((s) =>
          s.id === id ? { ...s, text } : s,
        ),
      })),
    removeSample: (id) =>
      setState((prev) => ({
        ...prev,
        writing_samples: prev.writing_samples.filter((s) => s.id !== id),
      })),
  };
}

function fieldActions(
  setState: SetState,
): Pick<
  UsePersonaFormResult,
  "setName" | "setText" | "setTone" | "addToList" | "removeFromList"
> {
  return {
    setName: (value) => setState((prev) => ({ ...prev, name: value })),
    setText: (key, value) => setState((prev) => ({ ...prev, [key]: value })),
    setTone: (key, value) =>
      setState((prev) => ({ ...prev, tone: { ...prev.tone, [key]: value } })),
    addToList: (key, raw) =>
      setState((prev) => ({ ...prev, [key]: addPhrase(prev[key], raw) })),
    removeFromList: (key, phrase) =>
      setState((prev) => ({
        ...prev,
        [key]: prev[key].filter((item) => item !== phrase),
      })),
  };
}

/** Local state, validation and dirty tracking of the persona create/edit form. */
export function usePersonaForm(persona?: PersonaProfile): UsePersonaFormResult {
  const [initial] = useState(() => initialPersonaFormState(persona));
  const [state, setState] = useState<PersonaFormState>(initial);
  const [addedSampleId, setAddedSampleId] = useState<string | null>(null);
  const errors = useMemo(() => validatePersonaForm(state), [state]);
  const dirty = useMemo(
    () => JSON.stringify(state) !== JSON.stringify(initial),
    [state, initial],
  );

  return {
    state,
    errors,
    isValid: Object.keys(errors).length === 0,
    dirty,
    addedSampleId,
    ...fieldActions(setState),
    ...sampleActions(setState, setAddedSampleId),
    toPayload: () => toPersonaPayload(state),
  };
}
