import { z } from "zod";
import {
  COVER_IDEA_COUNT_MAX,
  COVER_IDEA_COUNT_MIN,
  COVER_IDEA_LOCALES,
  COVER_IDEA_TOPIC_API_MAX,
  COVER_IDEA_TOPIC_MIN,
} from "@/constants/cover-prompt-ideas";
import { HEX_COLOUR_REGEX, paletteModeSchema } from "@/schemas/palette";

const hexColour = z.string().regex(HEX_COLOUR_REGEX);

/** The slide palette the ideas should suit (only its name, mode and colours). */
export const coverIdeasPaletteSchema = z.object({
  name: z.string().min(1).max(80),
  mode: paletteModeSchema,
  background: hexColour,
  primary: hexColour,
  accent: hexColour,
});

/**
 * `POST /carousels/cover-prompt-ideas`: the carousel topic, its palette (null for
 * "auto") and the dashboard locale. Nothing personal beyond the topic is sent.
 */
export const coverPromptIdeasRequestSchema = z.object({
  topic: z
    .string()
    .trim()
    .min(COVER_IDEA_TOPIC_MIN)
    .max(COVER_IDEA_TOPIC_API_MAX),
  palette: coverIdeasPaletteSchema.nullable(),
  locale: z.enum(COVER_IDEA_LOCALES),
});

/** Three to six AI prompt ideas for a new cover photo. */
export const coverPromptIdeasResponseSchema = z.object({
  ideas: z
    .array(z.string())
    .min(COVER_IDEA_COUNT_MIN)
    .max(COVER_IDEA_COUNT_MAX),
});

export type CoverIdeasPalette = z.infer<typeof coverIdeasPaletteSchema>;
export type CoverPromptIdeasRequest = z.infer<
  typeof coverPromptIdeasRequestSchema
>;
export type CoverPromptIdeasResponse = z.infer<
  typeof coverPromptIdeasResponseSchema
>;
