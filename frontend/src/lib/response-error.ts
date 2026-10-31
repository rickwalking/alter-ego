/**
 * The message of a failed API response, for UI error text.
 *
 * FastAPI sends `{"detail": "<message>"}` for handled errors but a list of
 * validation objects for a 422, and a proxy error may not be JSON at all. Only
 * a string `detail` is a user-facing message; anything else returns undefined
 * so the caller shows its own translated fallback (never "[object Object]").
 */
export async function responseErrorDetail(
  response: Response,
): Promise<string | undefined> {
  const body: unknown = await response.json().catch(() => null);
  if (body === null || typeof body !== "object" || !("detail" in body)) {
    return undefined;
  }
  return typeof body.detail === "string" ? body.detail : undefined;
}

/** The JSON body of a failed response, or null when it is not JSON. */
export async function responseErrorBody(response: Response): Promise<unknown> {
  return response
    .clone()
    .json()
    .catch(() => null);
}

/**
 * The stable `code` of an API error body (`{"detail": "...", "code": "..."}`),
 * or undefined when the body has no string `code`.
 */
export function errorBodyCode(body: unknown): string | undefined {
  if (body === null || typeof body !== "object" || !("code" in body)) {
    return undefined;
  }
  return typeof body.code === "string" ? body.code : undefined;
}

function locField(item: unknown): string | undefined {
  if (item === null || typeof item !== "object" || !("loc" in item)) {
    return undefined;
  }
  if (!Array.isArray(item.loc)) {
    return undefined;
  }
  const field: unknown = item.loc[item.loc.length - 1];
  return typeof field === "string" ? field : undefined;
}

/**
 * The request fields a FastAPI 422 body points at: the last `loc` segment of
 * each validation error (`["body", "password"]` gives `password`). Any other
 * body gives an empty list.
 */
export function validationErrorFields(body: unknown): string[] {
  if (body === null || typeof body !== "object" || !("detail" in body)) {
    return [];
  }
  if (!Array.isArray(body.detail)) {
    return [];
  }
  return body.detail
    .map(locField)
    .filter((field): field is string => field !== undefined);
}
