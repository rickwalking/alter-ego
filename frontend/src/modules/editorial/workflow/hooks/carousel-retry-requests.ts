import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  carouselRetryAcceptedSchema,
  carouselRetryCapabilitySchema,
  type CarouselRetryAccepted,
  type CarouselRetryCapability,
} from "@/schemas/carousel-retry";
import { requestCarouselRecovery } from "./carousel-reprocess-requests";

export function fetchCarouselRetryCapability(
  projectId: string,
): Promise<CarouselRetryCapability> {
  return requestCarouselRecovery(
    API_ENDPOINTS.CAROUSEL_RETRY(projectId),
    carouselRetryCapabilitySchema,
  );
}

export function postCarouselRetry(
  projectId: string,
  expectedVersion: number,
): Promise<CarouselRetryAccepted> {
  return requestCarouselRecovery(
    API_ENDPOINTS.CAROUSEL_RETRY(projectId),
    carouselRetryAcceptedSchema,
    {
      method: HTTP_METHODS.POST,
      body: JSON.stringify({ expected_version: expectedVersion }),
    },
  );
}
