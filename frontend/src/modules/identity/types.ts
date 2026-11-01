/**
 * `identity` — public type surface.
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
  /** True after an admin reset, until the user changes the password. */
  must_change_password: boolean;
}

export interface UseAuthResult {
  user: AuthUser | null;
  isLoading: boolean;
  isAdmin: boolean;
  isEditor: boolean;
  logout: () => void;
}

/** The three fields of the change-password form. */
export interface PasswordChangeValues {
  current: string;
  next: string;
  confirm: string;
}

/** Message keys (`account.password.errors.*`) of a refused password change. */
export type PasswordChangeErrorKey =
  | "currentIncorrect"
  | "unchanged"
  | "mismatch"
  | "tooShort"
  | "tooMany"
  | "failed";

/** State and actions of the change-password form. */
export interface ChangePasswordController {
  values: PasswordChangeValues;
  errorKey: PasswordChangeErrorKey | null;
  succeeded: boolean;
  isLoading: boolean;
  setField: (field: keyof PasswordChangeValues, value: string) => void;
  handleSubmit: (event: React.SubmitEvent) => Promise<void>;
}
