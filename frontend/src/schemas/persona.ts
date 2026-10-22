import { z } from "zod";

/** Mirrors `PersonaProfileCreate.name` (1–255 characters). */
export const PERSONA_NAME_MAX = 255;

/** The three `ToneAttributes` sliders, each `ge=0.0, le=1.0` on the backend. */
export const TONE_KEYS = ["formal", "conversational", "humorous"] as const;

export type ToneKey = (typeof TONE_KEYS)[number];

/** `ToneAttributes` defaults of the backend schema. */
export const DEFAULT_TONE: Record<ToneKey, number> = {
  formal: 0.3,
  conversational: 0.8,
  humorous: 0.4,
};

const unitInterval = z.number().min(0).max(1);
const optionalText = z.string().transform((value) => value.trim() || null);
const phraseList = z.array(z.string().trim().min(1));

/** The create/update payload the persona form sends (`PersonaProfileCreate`). */
export const personaFormSchema = z.object({
  name: z.string().trim().min(1).max(PERSONA_NAME_MAX),
  description: optionalText,
  tone_attributes: z.object({
    formal: unitInterval,
    conversational: unitInterval,
    humorous: unitInterval,
  }),
  writing_samples: z.array(z.string().trim().min(1)),
  forbidden_phrases: phraseList,
  preferred_phrases: phraseList,
  sentence_structure_preferences: optionalText,
  paragraph_style: optionalText,
  opinion_expression: optionalText,
  expertise_areas: phraseList,
});
