/**
 * Persona Profile Types
 */

export interface ToneAttributes {
  formal: number;
  conversational: number;
  humorous: number;
}

export interface PersonaProfile {
  id: string;
  name: string;
  description?: string | null;
  tone_attributes: ToneAttributes;
  writing_samples: string[];
  forbidden_phrases: string[];
  preferred_phrases: string[];
  sentence_structure_preferences?: string | null;
  paragraph_style?: string | null;
  opinion_expression?: string | null;
  expertise_areas: string[];
  created_at: string;
  updated_at: string;
  version: number;
}

export interface PersonaCreatePayload {
  name: string;
  description?: string | null;
  tone_attributes?: ToneAttributes | null;
  writing_samples?: string[];
  forbidden_phrases?: string[];
  preferred_phrases?: string[];
  sentence_structure_preferences?: string | null;
  paragraph_style?: string | null;
  opinion_expression?: string | null;
  expertise_areas?: string[];
}

export interface PersonaUpdatePayload {
  name?: string | null;
  description?: string | null;
  tone_attributes?: ToneAttributes | null;
  writing_samples?: string[] | null;
  forbidden_phrases?: string[] | null;
  preferred_phrases?: string[] | null;
  sentence_structure_preferences?: string | null;
  paragraph_style?: string | null;
  opinion_expression?: string | null;
  expertise_areas?: string[] | null;
}

export interface FeedbackPayload {
  original_text: string;
  corrected_text: string;
  context: string;
}
