"use client";

/** Hooks for blog AI endpoints. */

import { useCallback, useState } from "react";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type {
  BlogAiImproveResult,
  BlogAiSuggestResult,
  BlogGenerateImageResult,
  VoiceScoreResult,
} from "@/modules/publishing/blog/types-ai";
import type { UseBlogAiState } from "./types";

export function useBlogAi(postId: string | null) {
  const [state, setState] = useState<UseBlogAiState>({
    loading: false,
    error: null,
  });

  const suggest = useCallback(
    async (
      text: string,
      suggestionType: string,
      context?: string,
    ): Promise<BlogAiSuggestResult> => {
      if (!postId) {
        throw new Error("Post ID is required");
      }
      setState({ loading: true, error: null });
      try {
        const response = await authenticatedFetch(
          API_ENDPOINTS.BLOG_POST_AI_SUGGEST(postId),
          {
            method: HTTP_METHODS.POST,
            body: JSON.stringify({
              text,
              suggestion_type: suggestionType,
              context,
            }),
          },
        );
        if (!response.ok) {
          throw new Error("Failed to generate suggestion");
        }
        return (await response.json()) as BlogAiSuggestResult;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Suggestion failed";
        setState({ loading: false, error: message });
        throw err;
      } finally {
        setState((prev) => ({ ...prev, loading: false }));
      }
    },
    [postId],
  );

  const improve = useCallback(
    async (
      text: string,
      action: string,
      context?: string,
      personaId?: string,
    ): Promise<BlogAiImproveResult> => {
      if (!postId) {
        throw new Error("Post ID is required");
      }
      setState({ loading: true, error: null });
      try {
        const response = await authenticatedFetch(
          API_ENDPOINTS.BLOG_POST_AI_IMPROVE(postId),
          {
            method: HTTP_METHODS.POST,
            body: JSON.stringify({
              text,
              action,
              context,
              persona_id: personaId,
            }),
          },
        );
        if (!response.ok) {
          throw new Error("Failed to improve text");
        }
        return (await response.json()) as BlogAiImproveResult;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Improve failed";
        setState({ loading: false, error: message });
        throw err;
      } finally {
        setState((prev) => ({ ...prev, loading: false }));
      }
    },
    [postId],
  );

  const generateImage = useCallback(
    async (prompt: string): Promise<BlogGenerateImageResult> => {
      if (!postId) {
        throw new Error("Post ID is required");
      }
      setState({ loading: true, error: null });
      try {
        const response = await authenticatedFetch(
          API_ENDPOINTS.BLOG_POST_GENERATE_IMAGE(postId),
          {
            method: HTTP_METHODS.POST,
            body: JSON.stringify({ prompt }),
          },
        );
        if (!response.ok) {
          throw new Error("Image generation failed");
        }
        return (await response.json()) as BlogGenerateImageResult;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Image generation failed";
        setState({ loading: false, error: message });
        throw err;
      } finally {
        setState((prev) => ({ ...prev, loading: false }));
      }
    },
    [postId],
  );

  const scoreVoice = useCallback(
    async (personaId: string, text: string): Promise<VoiceScoreResult> => {
      setState({ loading: true, error: null });
      try {
        const response = await authenticatedFetch(
          API_ENDPOINTS.PERSONA_VOICE_SCORE(personaId),
          {
            method: HTTP_METHODS.POST,
            body: JSON.stringify({ text }),
          },
        );
        if (!response.ok) {
          throw new Error("Voice scoring failed");
        }
        return (await response.json()) as VoiceScoreResult;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Voice scoring failed";
        setState({ loading: false, error: message });
        throw err;
      } finally {
        setState((prev) => ({ ...prev, loading: false }));
      }
    },
    [],
  );

  return {
    ...state,
    suggest,
    improve,
    generateImage,
    scoreVoice,
  };
}
