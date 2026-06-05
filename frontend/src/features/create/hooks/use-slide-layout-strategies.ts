import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { carouselKeys } from "@/features/carousel/queries";

const STRATEGIES_QUERY_KEY = ["available-strategies"] as const;

const strategyInfoSchema = z.object({
  name: z.string(),
  display_name: z.string(),
});

const strategyListResponseSchema = z.object({
  strategies: z.array(strategyInfoSchema),
});

const applyStrategyResponseSchema = z.object({
  project_id: z.string(),
  strategy: z.string(),
  message: z.string(),
});

export type StrategyInfo = z.infer<typeof strategyInfoSchema>;

type StrategyListResponse = z.infer<typeof strategyListResponseSchema>;

type ApplyStrategyResponse = z.infer<typeof applyStrategyResponseSchema>;

export function useAvailableStrategies(): UseQueryResult<StrategyListResponse> {
  return useQuery({
    queryKey: STRATEGIES_QUERY_KEY,
    queryFn: async () => {
      return apiCall(
        API_ENDPOINTS.CAROUSEL_STRATEGIES,
        strategyListResponseSchema,
        { method: HTTP_METHODS.GET },
      );
    },
    staleTime: 1000 * 60 * 30,
  });
}

export function useRegenerateSlides(): UseMutationResult<
  ApplyStrategyResponse,
  Error,
  { projectId: string; strategy: string }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      projectId,
      strategy,
    }: {
      projectId: string;
      strategy: string;
    }) => {
      const params = new URLSearchParams({ name: strategy });
      const url = `${API_ENDPOINTS.CAROUSEL_STRATEGY_APPLY(projectId)}?${params.toString()}`;
      return apiCall(url, applyStrategyResponseSchema, {
        method: HTTP_METHODS.PUT,
      });
    },
    onSuccess: (_data, { projectId }) => {
      queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(projectId),
      });
    },
  });
}
