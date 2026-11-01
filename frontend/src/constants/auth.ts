/** Query param used when middleware sends unauthenticated users to login. */
export const AUTH_LOGIN_REDIRECT_PARAM = "redirect";

/** Request header carrying the public host behind the nginx proxy. */
export const HTTP_HEADER_HOST = "host";

/** Request header carrying the original request scheme behind the nginx proxy. */
export const HTTP_HEADER_X_FORWARDED_PROTO = "x-forwarded-proto";

/** Schemes accepted from the X-Forwarded-Proto header (defensive parse). */
export const FORWARDED_PROTOCOLS = ["http", "https"] as const;

/** Where a sign-in lands when the requested return path is missing or unsafe. */
export const DEFAULT_LOGIN_REDIRECT = "/dashboard/chat";

/** Placeholder origin used only to parse a return path as a same-origin URL. */
export const LOGIN_REDIRECT_PARSE_ORIGIN = "https://login-redirect.invalid";

/** How many rounds of percent-decoding a return path is checked through. */
export const LOGIN_REDIRECT_DECODE_ROUNDS = 3;

/**
 * The login form's no-JavaScript POST target (outside `/api`, which nginx sends
 * to FastAPI). With JavaScript the form posts JSON to the API instead.
 */
export const LOGIN_FORM_ACTION = "/auth/login";

/** Query param the login page reads to show a sign-in notice. */
export const LOGIN_ERROR_PARAM = "error";

/** `?error=` value after a failed no-JavaScript sign-in. */
export const LOGIN_ERROR_INVALID_CREDENTIALS = "invalid_credentials";

/** `?error=` value when the backend rate-limited a no-JavaScript sign-in. */
export const LOGIN_ERROR_TOO_MANY_ATTEMPTS = "too_many_attempts";

/** `?error=` value after the session expired (set by `/auth/logout`). */
export const LOGIN_ERROR_SESSION_EXPIRED = "session_expired";

/** Stable `code` of the 401 the API sends when a deactivated account signs in. */
export const LOGIN_ERROR_CODE_USER_INACTIVE = "user_inactive";

/**
 * Stable `code` values of the account API: the 403 sent until an admin-issued
 * password is changed, and the change-password refusals (wrong current
 * password, new password equal to the current one).
 */
export const ACCOUNT_ERROR_CODES = {
  CHANGE_REQUIRED: "password_change_required",
  CURRENT_INCORRECT: "current_password_incorrect",
  UNCHANGED: "password_unchanged",
} as const;
