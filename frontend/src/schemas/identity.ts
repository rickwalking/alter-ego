import { z } from "zod";

/**
 * Authenticated user returned by `/api/auth/me`.
 *
 * Mirrors {@link AuthUser} in `modules/identity/types`; the schema is the
 * runtime validation surface used by the TanStack Query `queryFn` (via the
 * shared `apiCall` client) so the session payload is validated, not cast.
 */
export const authUserSchema = z.object({
  id: z.string(),
  email: z.string(),
  full_name: z.string(),
  role: z.string(),
});

export type AuthUserSchema = z.infer<typeof authUserSchema>;
