import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
  type InfiniteData,
  type UseInfiniteQueryResult,
  type UseMutationResult,
} from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { HTTP_HEADER_IF_MATCH } from "@/constants/workflow";
import { carouselKeys } from "@/modules/carousel-presentation";
import type { CopyVersionRestoreInput } from "./types";
import { carouselCopyResponseSchema } from "./use-save-carousel-copy";

const COPY_VERSIONS_KEY = "copy-versions";

const copyVersionSchema = z.object({
  version_number: z.number(),
  field: z.string(),
  text: z.string(),
  author_id: z.string().nullable(),
  author_name: z.string().nullable(),
  created_at: z.string(),
  restored_from: z.number().nullable().optional(),
});

const copyVersionsResponseSchema = z.object({
  project_id: z.string(),
  versions: z.array(copyVersionSchema),
  next_before: z.number().nullable().optional(),
});

export type CopyVersionsResponse = z.infer<typeof copyVersionsResponseSchema>;
type CopyRestoreResponse = z.infer<typeof carouselCopyResponseSchema>;

/** Query key of a carousel's caption / LinkedIn versions. */
export const copyVersionsKey = (projectId: string) =>
  [...carouselKeys.detail(projectId), COPY_VERSIONS_KEY] as const;

/** The carousel's caption / LinkedIn versions, newest first, a page at a time. */
export function useCarouselCopyVersions(
  projectId: string,
): UseInfiniteQueryResult<InfiniteData<CopyVersionsResponse>> {
  return useInfiniteQuery({
    queryKey: copyVersionsKey(projectId),
    initialPageParam: undefined as number | undefined,
    queryFn: ({ pageParam }) =>
      apiCall(versionsUrl(projectId, pageParam), copyVersionsResponseSchema),
    getNextPageParam: (last) => last.next_before ?? undefined,
  });
}

function versionsUrl(projectId: string, before: number | undefined): string {
  const base = API_ENDPOINTS.CAROUSEL_COPY_VERSIONS(projectId);
  return before === undefined ? base : `${base}?before=${before}`;
}

/**
 * Restore a stored version with the loaded ``lock_version`` as ``If-Match``;
 * the response carries the saved texts and the next lock version.
 */
export function useRestoreCopyVersion(): UseMutationResult<
  CopyRestoreResponse,
  Error,
  CopyVersionRestoreInput
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      lockVersion,
      versionNumber,
    }: CopyVersionRestoreInput) =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_COPY_VERSION_RESTORE(projectId, versionNumber),
        carouselCopyResponseSchema,
        {
          method: HTTP_METHODS.POST,
          headers: { [HTTP_HEADER_IF_MATCH]: String(lockVersion) },
        },
      ),
    onSettled: (_data, _error, { projectId }) => {
      void queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(projectId),
      });
    },
  });
}
