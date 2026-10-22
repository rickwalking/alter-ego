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
