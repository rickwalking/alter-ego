/**
 * `identity` — TanStack Query options + keys for the client session (AE-0184).
 *
 * The session probe (`/api/auth/me`) is intentionally routed through the shared
 * `authenticatedFetch` client rather than `apiCall`: a 401 here means "logged
 * out", an expected state that resolves to `null`, NOT an error that should
 * trigger the api-client's login redirect. The logout call is an imperative
 * POST exposed as a mutation.
 */
import { queryOptions } from "@tanstack/react-query";

import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { authUserSchema } from "@/schemas/identity";
import type { AuthUser } from "./types";

export const authKeys = {
  currentUser: () => ["auth", "me"] as const,
};

/**
 * Fetch the current session user, resolving to `null` when unauthenticated
 * (non-2xx) or when the payload fails validation.
 */
async function fetchCurrentUser(): Promise<AuthUser | null> {
  const response = await authenticatedFetch(API_ENDPOINTS.AUTH_ME);
  if (!response.ok) {
    return null;
  }
  const parsed = authUserSchema.safeParse(await response.json());
  return parsed.success ? parsed.data : null;
}

export function currentUserOptions() {
  return queryOptions({
    queryKey: authKeys.currentUser(),
    queryFn: fetchCurrentUser,
  });
}

/** Best-effort backend logout; network errors are swallowed by the caller. */
export async function postLogout(): Promise<void> {
  await authenticatedFetch(API_ENDPOINTS.AUTH_LOGOUT, {
    method: HTTP_METHODS.POST,
  });
}
