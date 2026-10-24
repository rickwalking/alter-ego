import { useMutation } from "@tanstack/react-query";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  coverPromptIdeasRequestSchema,
  coverPromptIdeasResponseSchema,
  type CoverPromptIdeasRequest,
  type CoverPromptIdeasResponse,
} from "@/schemas/cover-prompt-ideas";

/**
 * "Mais ideias": AI prompt ideas for a new cover photo; nothing is saved. The
 * request is parsed before it is sent (trimmed topic, strict palette, locale).
 */
export function useCoverPromptIdeas() {
  return useMutation({
    mutationFn: (data: CoverPromptIdeasRequest) =>
      apiCall<CoverPromptIdeasResponse>(
        API_ENDPOINTS.COVER_PROMPT_IDEAS,
        coverPromptIdeasResponseSchema,
        {
          method: HTTP_METHODS.POST,
          body: JSON.stringify(coverPromptIdeasRequestSchema.parse(data)),
        },
      ),
  });
}
