"use client";

import { useCallback, useMemo, useState } from "react";
import type {
  QualityRubric,
  QualityRubricCreatePayload,
} from "@/modules/quality";
import {
  initialRubricFormState,
  moveItem,
  newCriterion,
  toRubricPayload,
  validateRubricForm,
  type CriterionDraft,
  type RubricFormErrors,
  type RubricFormState,
} from "./rubric-form-model";

type CriterionField = Exclude<keyof CriterionDraft, "id">;

export interface CriterionEdit {
  index: number;
  field: CriterionField;
  value: string;
}

export interface UseRubricFormResult {
  state: RubricFormState;
  errors: RubricFormErrors;
  isValid: boolean;
  /** True once the values differ from the ones the form opened with. */
  dirty: boolean;
  /** The id of the criterion added last (its name field takes focus). */
  addedId: string | null;
  setName: (value: string) => void;
  setDescription: (value: string) => void;
  toggleContentType: (type: string) => void;
  addCriterion: () => void;
  removeCriterion: (index: number) => void;
  moveCriterion: (index: number, offset: number) => void;
  setCriterionField: (edit: CriterionEdit) => void;
  toPayload: () => QualityRubricCreatePayload;
}

function toggled(list: readonly string[], value: string): string[] {
  return list.includes(value)
    ? list.filter((item) => item !== value)
    : [...list, value];
}

function useCriteriaActions(
  setState: React.Dispatch<React.SetStateAction<RubricFormState>>,
  setAddedId: (id: string) => void,
): Pick<
  UseRubricFormResult,
  "addCriterion" | "removeCriterion" | "moveCriterion" | "setCriterionField"
> {
  const update = useCallback(
    (fn: (criteria: CriterionDraft[]) => CriterionDraft[]) =>
      setState((prev) => ({ ...prev, criteria: fn(prev.criteria) })),
    [setState],
  );
  return {
    addCriterion: useCallback(() => {
      const criterion = newCriterion();
      setAddedId(criterion.id);
      update((criteria) => [...criteria, criterion]);
    }, [update, setAddedId]),
    removeCriterion: useCallback(
      (index: number) => update((c) => c.filter((_, i) => i !== index)),
      [update],
    ),
    moveCriterion: useCallback(
      (index: number, offset: number) =>
        update((c) => moveItem(c, index, offset)),
      [update],
    ),
    setCriterionField: useCallback(
      ({ index, field, value }: CriterionEdit) =>
        update((c) =>
          c.map((item, i) =>
            i === index ? { ...item, [field]: value } : item,
          ),
        ),
      [update],
    ),
  };
}

/** Local state, validation and dirty tracking of the rubric create/edit form. */
export function useRubricForm(rubric?: QualityRubric): UseRubricFormResult {
  const [initial] = useState(() => initialRubricFormState(rubric));
  const [state, setState] = useState<RubricFormState>(initial);
  const [addedId, setAddedId] = useState<string | null>(null);
  const errors = useMemo(() => validateRubricForm(state), [state]);
  const dirty = useMemo(
    () => JSON.stringify(state) !== JSON.stringify(initial),
    [state, initial],
  );
  const criteriaActions = useCriteriaActions(setState, setAddedId);

  return {
    state,
    errors,
    isValid: Object.keys(errors).length === 0,
    dirty,
    addedId,
    setName: (value) => setState((prev) => ({ ...prev, name: value })),
    setDescription: (value) =>
      setState((prev) => ({ ...prev, description: value })),
    toggleContentType: (type) =>
      setState((prev) => ({
        ...prev,
        applicable_content_types: toggled(prev.applicable_content_types, type),
      })),
    ...criteriaActions,
    toPayload: () => toRubricPayload(state),
  };
}
