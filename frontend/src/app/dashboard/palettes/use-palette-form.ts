"use client";

import {
  useCallback,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import {
  HEX_COLOUR_REGEX,
  PALETTE_MODES,
  type CustomPalette,
  type PaletteCandidate,
  type PaletteCreateRequest,
  type PaletteMode,
} from "@/schemas/palette";

const NAME_MIN = 1;
const NAME_MAX = 80;
const KEYWORD_MAX_COUNT = 10;

const NEW_PALETTE_DEFAULT = {
  name: "",
  primary: "#22d3ee",
  accent: "#a855f7",
  background: "#0a0e17",
  mode: PALETTE_MODES[1] satisfies PaletteMode,
  keywords: [] as string[],
};

export interface PaletteFormState {
  name: string;
  primary: string;
  accent: string;
  background: string;
  mode: PaletteMode;
  keywords: string[];
}

export interface PaletteFormErrors {
  name?: string;
  primary?: string;
  accent?: string;
  background?: string;
}

function initialState(palette?: CustomPalette): PaletteFormState {
  if (!palette) return { ...NEW_PALETTE_DEFAULT };
  return {
    name: palette.name,
    primary: palette.primary,
    accent: palette.accent,
    background: palette.background,
    mode: palette.mode,
    keywords: [...palette.keywords],
  };
}

/**
 * Mirrors the backend guards: name length cap and no angle brackets (XSS),
 * plus hex colours.
 */
function validate(state: PaletteFormState): PaletteFormErrors {
  const errors: PaletteFormErrors = {};
  const name = state.name.trim();
  if (
    name.length < NAME_MIN ||
    name.length > NAME_MAX ||
    name.includes("<") ||
    name.includes(">")
  ) {
    errors.name = "name";
  }
  for (const field of ["primary", "accent", "background"] as const) {
    if (!HEX_COLOUR_REGEX.test(state[field])) errors[field] = "hex";
  }
  return errors;
}

/** Normalise a raw keyword entry: trim + lowercase (mirrors the backend guard). */
function cleanKeyword(raw: string): string {
  return raw.trim().toLowerCase();
}

export interface UsePaletteFormResult {
  state: PaletteFormState;
  errors: PaletteFormErrors;
  isValid: boolean;
  setField: <K extends keyof PaletteFormState>(
    key: K,
    value: PaletteFormState[K],
  ) => void;
  addKeywords: (raw: string) => void;
  removeKeyword: (keyword: string) => void;
  /** Replace every field with an AI candidate's values (nothing is saved). */
  applyCandidate: (candidate: PaletteCandidate) => void;
  /** The full field set — valid as both a create and a (full) update payload. */
  toRequest: () => PaletteCreateRequest;
}

/** The form state an AI candidate pre-fills (keywords capped like manual entry). */
function candidateState(candidate: PaletteCandidate): PaletteFormState {
  return {
    name: candidate.name,
    primary: candidate.primary,
    accent: candidate.accent,
    background: candidate.background,
    mode: candidate.mode,
    keywords: candidate.keywords.slice(0, KEYWORD_MAX_COUNT),
  };
}

/** Add (comma-separated, deduped, capped) and remove keyword chips. */
function useKeywordActions(
  setState: Dispatch<SetStateAction<PaletteFormState>>,
): Pick<UsePaletteFormResult, "addKeywords" | "removeKeyword"> {
  const addKeywords = useCallback(
    (raw: string) => {
      const additions = raw.split(",").map(cleanKeyword).filter(Boolean);
      if (additions.length === 0) return;
      setState((prev) => {
        const next = [...prev.keywords];
        for (const keyword of additions) {
          if (!next.includes(keyword) && next.length < KEYWORD_MAX_COUNT) {
            next.push(keyword);
          }
        }
        return { ...prev, keywords: next };
      });
    },
    [setState],
  );

  const removeKeyword = useCallback(
    (keyword: string) => {
      setState((prev) => ({
        ...prev,
        keywords: prev.keywords.filter((item) => item !== keyword),
      }));
    },
    [setState],
  );

  return { addKeywords, removeKeyword };
}

/** Local form state + client-side validation for the palette create/edit modal. */
export function usePaletteForm(palette?: CustomPalette): UsePaletteFormResult {
  const [state, setState] = useState<PaletteFormState>(() =>
    initialState(palette),
  );
  const errors = useMemo(() => validate(state), [state]);
  const isValid = Object.keys(errors).length === 0;

  const setField = useCallback<UsePaletteFormResult["setField"]>(
    (key, value) => setState((prev) => ({ ...prev, [key]: value })),
    [],
  );

  const { addKeywords, removeKeyword } = useKeywordActions(setState);

  const applyCandidate = useCallback(
    (candidate: PaletteCandidate) => setState(candidateState(candidate)),
    [],
  );

  const toRequest = useCallback(
    (): PaletteCreateRequest => ({
      name: state.name.trim(),
      primary: state.primary,
      accent: state.accent,
      background: state.background,
      mode: state.mode,
      keywords: state.keywords,
    }),
    [state],
  );

  return {
    state,
    errors,
    isValid,
    setField,
    addKeywords,
    removeKeyword,
    applyCandidate,
    toRequest,
  };
}

export { KEYWORD_MAX_COUNT, NAME_MAX };
