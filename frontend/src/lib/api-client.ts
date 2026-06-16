import { z } from "zod";

import { HTTP_STATUS } from "@/constants/api";
import { AUTH_LOGIN_REDIRECT_PARAM } from "@/constants/auth";

// API Response Schema
export const apiResponseSchema = z.object({
  success: z.boolean(),
  data: z.unknown(),
  message: z.string().optional(),
});

// Error Response Schema
export const errorResponseSchema = z.object({
  success: z.literal(false),
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.unknown().optional(),
  }),
});

export type ApiResponse = z.infer<typeof apiResponseSchema>;
export type ErrorResponse = z.infer<typeof errorResponseSchema>;

function redirectToLoginAfterUnauthorized(): void {
  if (typeof window === "undefined") {
    return;
  }
  const redirect = `${window.location.pathname}${window.location.search}`;
  const params = new URLSearchParams();
  params.set(AUTH_LOGIN_REDIRECT_PARAM, redirect);
  window.location.href = `/api/auth/logout?${params.toString()}`;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ApiErrorBody {
  message?: string;
  code?: string;
}

const FORBIDDEN_REDIRECT_PATH = "/403";
const JSON_CONTENT_TYPE = "application/json";

async function parseErrorBody(
  response: Response,
): Promise<ApiErrorBody | null> {
  return (await response.json().catch(() => null)) as ApiErrorBody | null;
}

/** Issue a credentialed JSON fetch (shared by apiCall + apiCallNoContent). */
function fetchWithCredentials(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  return fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": JSON_CONTENT_TYPE,
      ...options?.headers,
    },
  });
}

/**
 * Map non-OK HTTP statuses to `ApiError`, threading the 401 login redirect and
 * the 403 page redirect. Returns normally when the response is OK; the caller
 * then parses the body (or skips it, for No Content responses).
 */
async function throwIfErrorResponse(response: Response): Promise<void> {
  if (response.status === HTTP_STATUS.UNAUTHORIZED) {
    const errorData = await parseErrorBody(response);
    redirectToLoginAfterUnauthorized();
    throw new ApiError(
      HTTP_STATUS.UNAUTHORIZED,
      errorData?.message || "Unauthorized",
      errorData?.code,
    );
  }

  if (response.status === HTTP_STATUS.FORBIDDEN) {
    const errorData = await parseErrorBody(response);
    if (typeof window !== "undefined") {
      window.location.href = FORBIDDEN_REDIRECT_PATH;
    }
    throw new ApiError(
      HTTP_STATUS.FORBIDDEN,
      errorData?.message || "Forbidden",
      errorData?.code,
    );
  }

  if (!response.ok) {
    const errorData = await parseErrorBody(response);
    throw new ApiError(
      response.status,
      errorData?.message || `HTTP error! status: ${response.status}`,
      errorData?.code,
    );
  }
}

export async function apiCall<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: RequestInit,
): Promise<T> {
  const response = await fetchWithCredentials(url, options);
  await throwIfErrorResponse(response);

  const json = await response.json();

  // Support both wrapped {success, data} and direct responses
  const responseResult = apiResponseSchema.safeParse(json);
  if (responseResult.success) {
    if (!responseResult.data.success) {
      const errorResult = errorResponseSchema.safeParse(json);
      if (errorResult.success) {
        throw new ApiError(
          HTTP_STATUS.BAD_REQUEST,
          errorResult.data.error.message,
          errorResult.data.error.code,
        );
      }
      throw new ApiError(HTTP_STATUS.BAD_REQUEST, "API request failed");
    }
    const dataResult = schema.safeParse(responseResult.data.data);
    if (!dataResult.success) {
      console.error("Data validation failed:", dataResult.error.issues);
      throw new ApiError(
        HTTP_STATUS.INTERNAL_SERVER_ERROR,
        "Invalid data from API",
      );
    }
    return dataResult.data;
  }

  // Direct response — validate against provided schema
  const dataResult = schema.safeParse(json);
  if (!dataResult.success) {
    console.error("Data validation failed:", dataResult.error.issues);
    throw new ApiError(
      HTTP_STATUS.INTERNAL_SERVER_ERROR,
      "Invalid data from API",
    );
  }
  return dataResult.data;
}

/**
 * Issue a request that expects no response body (DELETE → 204, POST → 204).
 *
 * Threads the same error-handling path as `apiCall` so callers get
 * `ApiError` with the server's status and message, but skips the JSON
 * parse step that would otherwise fail on a 204 No Content response.
 */
export async function apiCallNoContent(
  url: string,
  options?: RequestInit,
): Promise<void> {
  const response = await fetchWithCredentials(url, options);
  await throwIfErrorResponse(response);
}
