import { z } from "zod";
import { HTTP_METHODS } from "@/constants/api";
import { WORKFLOW_API } from "@/constants/workflow";
import { ApiError } from "@/lib/api-client";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  carouselReprocessCapabilitySchema,
  manualReprocessResponseSchema,
  type CarouselReprocessCapability,
  type ManualReprocessResponse,
} from "@/schemas/carousel-reprocess";
import type { CarouselReprocessRequest } from "./types";

const REQUEST_FAILED = "Carousel reprocess request failed";
const errorDetailSchema = z.object({ detail: z.string() });

async function readRequestError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch((): null => null);
  const parsed = errorDetailSchema.safeParse(body);
  const error = new ApiError(response.status, REQUEST_FAILED);
  if (parsed.success) error.detail = parsed.data.detail;
  return error;
}

async function requestReprocess<T>(
  url: string,
  schema: z.ZodType<T>,
  options?: RequestInit,
): Promise<T> {
  const response = await authenticatedFetch(url, options);
  if (!response.ok) throw await readRequestError(response);
  const body: unknown = await response.json();
  return schema.parse(body);
}

export function fetchCarouselReprocessCapability(
  projectId: string,
): Promise<CarouselReprocessCapability> {
  return requestReprocess(
    WORKFLOW_API.CAROUSEL_REPROCESS(projectId),
    carouselReprocessCapabilitySchema,
  );
}

export function postCarouselReprocess(
  projectId: string,
  input: CarouselReprocessRequest,
): Promise<ManualReprocessResponse> {
  return requestReprocess(
    WORKFLOW_API.CAROUSEL_REPROCESS(projectId),
    manualReprocessResponseSchema,
    {
      method: HTTP_METHODS.POST,
      body: JSON.stringify({
        expected_version: input.expectedVersion,
        ...(input.runId === null ? {} : { run_id: input.runId }),
      }),
    },
  );
}
