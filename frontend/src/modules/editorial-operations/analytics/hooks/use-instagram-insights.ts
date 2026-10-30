import { useQuery } from "@tanstack/react-query";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS } from "@/constants/api";
import {
  instagramInsightsSchema,
  type InstagramInsights,
} from "./instagram-insights-schema";

export type {
  InstagramConnector,
  InstagramInsights,
  InstagramPostInsights,
} from "./instagram-insights-schema";

export const instagramInsightsKeys = {
  all: ["instagram-insights"] as const,
};

/** Per-post Instagram metrics for the dashboard KPI card. */
export function useInstagramInsights() {
  return useQuery({
    queryKey: instagramInsightsKeys.all,
    queryFn: (): Promise<InstagramInsights> =>
      apiCall(API_ENDPOINTS.INSTAGRAM_INSIGHTS, instagramInsightsSchema),
  });
}
