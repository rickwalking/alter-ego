import { z } from "zod";

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

export async function apiCall<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (response.status === 401) {
    const errorData = await response.json().catch(() => null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(
      401,
      errorData?.message || "Unauthorized",
      errorData?.code,
    );
  }

  if (response.status === 403) {
    const errorData = await response.json().catch(() => null);
    if (typeof window !== "undefined") {
      window.location.href = "/403";
    }
    throw new ApiError(403, errorData?.message || "Forbidden", errorData?.code);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      errorData?.message || `HTTP error! status: ${response.status}`,
      errorData?.code,
    );
  }

  const json = await response.json();

  // Support both wrapped {success, data} and direct responses
  const responseResult = apiResponseSchema.safeParse(json);
  if (responseResult.success) {
    if (!responseResult.data.success) {
      const errorResult = errorResponseSchema.safeParse(json);
      if (errorResult.success) {
        throw new ApiError(
          400,
          errorResult.data.error.message,
          errorResult.data.error.code,
        );
      }
      throw new ApiError(400, "API request failed");
    }
    const dataResult = schema.safeParse(responseResult.data.data);
    if (!dataResult.success) {
      console.error("Data validation failed:", dataResult.error.issues);
      throw new ApiError(500, "Invalid data from API");
    }
    return dataResult.data;
  }

  // Direct response — validate against provided schema
  const dataResult = schema.safeParse(json);
  if (!dataResult.success) {
    console.error("Data validation failed:", dataResult.error.issues);
    throw new ApiError(500, "Invalid data from API");
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
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (response.status === 401) {
    const errorData = await response.json().catch(() => null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(
      401,
      errorData?.message || "Unauthorized",
      errorData?.code,
    );
  }

  if (response.status === 403) {
    const errorData = await response.json().catch(() => null);
    if (typeof window !== "undefined") {
      window.location.href = "/403";
    }
    throw new ApiError(403, errorData?.message || "Forbidden", errorData?.code);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      errorData?.message || `HTTP error! status: ${response.status}`,
      errorData?.code,
    );
  }
}
