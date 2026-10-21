import { z } from "zod";

import { HTTP_STATUS } from "@/constants/api";
import { AUTH_LOGIN_REDIRECT_PARAM } from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";

export const apiResponseSchema = z.object({
  success: z.boolean(),
  data: z.unknown(),
  message: z.string().optional(),
});

export const errorResponseSchema = z.object({
  success: z.literal(false),
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.unknown().optional(),
  }),
});

function redirectToLoginAfterUnauthorized(): void {
  if (typeof window === "undefined") {
    return;
  }
  const redirect = `${window.location.pathname}${window.location.search}`;
  const params = new URLSearchParams();
  params.set(AUTH_LOGIN_REDIRECT_PARAM, redirect);
  window.location.href = `${PUBLIC_ROUTE_PATHS.LOGOUT}?${params.toString()}`;
}

export class ApiError extends Error {
  /** The raw FastAPI `detail` (e.g. the 422 validation list). */
  public detail?: unknown;

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
  detail?: unknown;
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
      ...(options?.headers as Record<string, string> | undefined),
    },
  });
}

/** Message used when an auth error body carries none. */
const AUTH_FALLBACK_MESSAGES: Readonly<Partial<Record<number, string>>> = {
  [HTTP_STATUS.UNAUTHORIZED]: "Unauthorized",
  [HTTP_STATUS.FORBIDDEN]: "Forbidden",
};

/** The 401 login redirect and the 403 page redirect. */
function redirectForAuthStatus(status: number): void {
  if (status === HTTP_STATUS.UNAUTHORIZED) {
    redirectToLoginAfterUnauthorized();
    return;
  }
  if (status === HTTP_STATUS.FORBIDDEN && typeof window !== "undefined") {
    window.location.href = FORBIDDEN_REDIRECT_PATH;
  }
}

/**
 * Map non-OK HTTP statuses to `ApiError`, threading the 401 login redirect and
 * the 403 page redirect. Returns normally when the response is OK; the caller
 * then parses the body (or skips it, for No Content responses).
 */
async function throwIfErrorResponse(response: Response): Promise<void> {
  if (response.ok) {
    return;
  }
  const { status } = response;
  const errorData = await parseErrorBody(response);
  redirectForAuthStatus(status);
  const authFallback = AUTH_FALLBACK_MESSAGES[status];
  const error = new ApiError(
    status,
    errorData?.message ?? authFallback ?? `HTTP error! status: ${status}`,
    errorData?.code,
  );
  if (authFallback === undefined) {
    error.detail = errorData?.detail;
  }
  throw error;
}

/** Validate API data against the caller's schema (500 on a contract break). */
function parseApiData<T>(schema: z.ZodSchema<T>, data: unknown): T {
  const dataResult = schema.safeParse(data);
  if (!dataResult.success) {
    console.error("Data validation failed:", dataResult.error.issues);
    throw new ApiError(
      HTTP_STATUS.INTERNAL_SERVER_ERROR,
      "Invalid data from API",
    );
  }
  return dataResult.data;
}

/** The `{success:false, error}` envelope as an `ApiError`. */
function envelopeError(json: unknown): ApiError {
  const errorResult = errorResponseSchema.safeParse(json);
  if (errorResult.success) {
    return new ApiError(
      HTTP_STATUS.BAD_REQUEST,
      errorResult.data.error.message,
      errorResult.data.error.code,
    );
  }
  return new ApiError(HTTP_STATUS.BAD_REQUEST, "API request failed");
}

/** Accepts both the wrapped {success, data} envelope and direct responses. */
export async function apiCall<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: RequestInit,
): Promise<T> {
  const response = await fetchWithCredentials(url, options);
  await throwIfErrorResponse(response);

  const json: unknown = await response.json();

  const responseResult = apiResponseSchema.safeParse(json);
  if (!responseResult.success) {
    return parseApiData(schema, json);
  }
  if (!responseResult.data.success) {
    throw envelopeError(json);
  }
  return parseApiData(schema, responseResult.data.data);
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

/**
 * POST a multipart form (file upload) and validate the JSON reply.
 *
 * Unlike `apiCall` it sends no JSON `Content-Type`, so the browser sets the
 * multipart boundary; errors go through the same `ApiError` path.
 */
export async function apiUpload<T>(
  url: string,
  schema: z.ZodSchema<T>,
  form: FormData,
): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    body: form,
    credentials: "include",
  });
  await throwIfErrorResponse(response);
  return schema.parse(await response.json());
}
