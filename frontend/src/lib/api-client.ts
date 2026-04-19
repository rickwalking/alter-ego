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
    public code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiCall<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      errorData?.message || `HTTP error! status: ${response.status}`,
      errorData?.code
    );
  }

  const json = await response.json();

  // Validate response structure
  const responseResult = apiResponseSchema.safeParse(json);
  if (!responseResult.success) {
    throw new ApiError(500, "Invalid API response structure");
  }

  if (!responseResult.data.success) {
    const errorResult = errorResponseSchema.safeParse(json);
    if (errorResult.success) {
      throw new ApiError(
        400,
        errorResult.data.error.message,
        errorResult.data.error.code
      );
    }
    throw new ApiError(400, "API request failed");
  }

  // Validate data with provided schema
  const dataResult = schema.safeParse(responseResult.data.data);
  if (!dataResult.success) {
    console.error("Data validation failed:", dataResult.error.issues);
    throw new ApiError(500, "Invalid data from API");
  }

  return dataResult.data;
}
