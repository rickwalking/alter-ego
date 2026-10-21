"use client";

/** Hooks for blog AI endpoints. */

import { useCallback, useState } from "react";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type {
  BlogAiImproveResult,
  BlogAiSuggestResult,
  VoiceScoreResult,
} from "@/modules/publishing/blog/types-ai";
import type { BlogAiImproveParams, SuggestArgs, UseBlogAiState } from "./types";

const ERR_POST_ID_REQUIRED = "Post ID is required";

/** POST a JSON body; a non-OK status throws ``failure``. */
async function postAiJson<T>(
  url: string,
  body: Record<string, unknown>,
  failure: string,
): Promise<T> {
  const response = await authenticatedFetch(url, {
    method: HTTP_METHODS.POST,
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(failure);
  }
  return (await response.json()) as T;
}

function requirePostId(postId: string | null): string {
  if (!postId) {
    throw new Error(ERR_POST_ID_REQUIRED);
  }
  return postId;
}

type TrackAiRequest = <T>(
  request: () => Promise<T>,
  fallbackMessage: string,
) => Promise<T>;

/** Loading/error state around one AI request at a time (errors re-thrown). */
function useAiRequestState(): [UseBlogAiState, TrackAiRequest] {
  const [state, setState] = useState<UseBlogAiState>({
    loading: false,
    error: null,
  });
  const track = useCallback(
    async <T>(
      request: () => Promise<T>,
      fallbackMessage: string,
    ): Promise<T> => {
      setState({ loading: true, error: null });
      try {
        return await request();
      } catch (err) {
        const message = err instanceof Error ? err.message : fallbackMessage;
        setState({ loading: false, error: message });
        throw err;
      } finally {
        setState((prev) => ({ ...prev, loading: false }));
      }
    },
    [],
  );
  return [state, track];
}

function requestSuggestion(
  postId: string,
  { text, suggestionType, context }: SuggestArgs,
): Promise<BlogAiSuggestResult> {
  return postAiJson<BlogAiSuggestResult>(
    API_ENDPOINTS.BLOG_POST_AI_SUGGEST(postId),
    { text, suggestion_type: suggestionType, context },
    "Failed to generate suggestion",
  );
}

function requestImprovement(
  postId: string,
  { text, action, context, personaId }: BlogAiImproveParams,
): Promise<BlogAiImproveResult> {
  return postAiJson<BlogAiImproveResult>(
    API_ENDPOINTS.BLOG_POST_AI_IMPROVE(postId),
    { text, action, context, persona_id: personaId },
    "Failed to improve text",
  );
}

function requestVoiceScore(
  personaId: string,
  text: string,
): Promise<VoiceScoreResult> {
  return postAiJson<VoiceScoreResult>(
    API_ENDPOINTS.PERSONA_VOICE_SCORE(personaId),
    { text },
    "Voice scoring failed",
  );
}

export function useBlogAi(postId: string | null) {
  const [state, track] = useAiRequestState();

  const suggest = useCallback(
    async (
      text: string,
      suggestionType: string,
      context?: string,
    ): Promise<BlogAiSuggestResult> => {
      const id = requirePostId(postId);
      return track(
        () => requestSuggestion(id, { text, suggestionType, context }),
        "Suggestion failed",
      );
    },
    [postId, track],
  );

  const improve = useCallback(
    async (params: BlogAiImproveParams): Promise<BlogAiImproveResult> => {
      const id = requirePostId(postId);
      return track(() => requestImprovement(id, params), "Improve failed");
    },
    [postId, track],
  );

  const scoreVoice = useCallback(
    async (personaId: string, text: string): Promise<VoiceScoreResult> =>
      track(() => requestVoiceScore(personaId, text), "Voice scoring failed"),
    [track],
  );

  return { ...state, suggest, improve, scoreVoice };
}
