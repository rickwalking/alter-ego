/**
 * `identity` — public type surface (AE-0156).
 *
 * Object-shape types for the identity hooks and JWT lib live here so the
 * component-type-location ratchet (`npm run lint:component-types`) stays green
 * once these files live under `src/modules/**`.
 */

export interface AccessTokenPayload {
  sub: string;
  email: string;
  role: string;
  type: string;
  exp: number;
  iat: number;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface UseAuthResult {
  user: AuthUser | null;
  isLoading: boolean;
  isAdmin: boolean;
  isEditor: boolean;
  logout: () => void;
}
