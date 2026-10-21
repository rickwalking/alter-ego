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
