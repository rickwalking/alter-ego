import { NextRequest, NextResponse } from "next/server";

import {
  CONTENT_TYPES,
  HTTP_METHODS,
  resolveBackendUrl,
} from "@/constants/api";
import {
  DEFAULT_LOGIN_REDIRECT,
  HTTP_HEADER_HOST,
  LOGIN_ERROR_INVALID_CREDENTIALS,
  LOGIN_ERROR_PARAM,
  LOGIN_ERROR_TOO_MANY_ATTEMPTS,
} from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { setAccessTokenCookie } from "@/modules/identity";

const HTTP_SEE_OTHER = 303;
const HTTP_FORBIDDEN = 403;
const HTTP_TOO_MANY_REQUESTS = 429;
const HEADER_ORIGIN = "origin";
const HEADER_SEC_FETCH_SITE = "sec-fetch-site";
const SAME_ORIGIN_FETCH_SITES: ReadonlySet<string> = new Set([
  "same-origin",
  "none",
]);
const OPAQUE_ORIGIN = "null";
const FIELD_EMAIL = "email";
const FIELD_PASSWORD = "password";

interface TokenPayload {
  access_token?: string;
}

/** The backend's answer: a token, or the `?error=` code to show on the login page. */
type SignInResult = { token: string } | { error: string };

/** The login page with an error code only (never the submitted fields). */
function failedLoginPath(error: string): string {
  const query = new URLSearchParams({ [LOGIN_ERROR_PARAM]: error });
  return `${PUBLIC_ROUTE_PATHS.LOGIN}?${query.toString()}`;
}

/** A 303 to a same-origin path (relative `Location`, so no host is rebuilt). */
function seeOther(path: string): NextResponse {
  return new NextResponse(null, {
    status: HTTP_SEE_OTHER,
    headers: { Location: path },
  });
}

/**
 * Whether the post came from this site's own page (no login CSRF). The site's
 * `no-referrer` policy makes browsers send `Origin: null` on this post, so the
 * Fetch Metadata header decides when present; otherwise a real `Origin` must
 * name this host, and an opaque or missing one is refused.
 */
function isSameOriginPost(request: NextRequest): boolean {
  const fetchSite = request.headers.get(HEADER_SEC_FETCH_SITE);
  if (fetchSite) return SAME_ORIGIN_FETCH_SITES.has(fetchSite);
  const origin = request.headers.get(HEADER_ORIGIN);
  const host = request.headers.get(HTTP_HEADER_HOST);
  if (!origin || origin === OPAQUE_ORIGIN || !host) return false;
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

const INVALID_CREDENTIALS: SignInResult = {
  error: LOGIN_ERROR_INVALID_CREDENTIALS,
};

async function signIn(email: string, password: string): Promise<SignInResult> {
  const response = await fetch(`${resolveBackendUrl()}/api/auth/token`, {
    method: HTTP_METHODS.POST,
    headers: { "Content-Type": CONTENT_TYPES.JSON },
    body: JSON.stringify({ email, password }),
  });
  if (response.status === HTTP_TOO_MANY_REQUESTS) {
    return { error: LOGIN_ERROR_TOO_MANY_ATTEMPTS };
  }
  if (!response.ok) return INVALID_CREDENTIALS;
  try {
    const payload = (await response.json()) as TokenPayload;
    return payload.access_token
      ? { token: payload.access_token }
      : INVALID_CREDENTIALS;
  } catch {
    return INVALID_CREDENTIALS;
  }
}

/**
 * Sign-in for a login form submitted before (or without) JavaScript: the form
 * posts here instead of falling back to a GET that would put the email and
 * password in the URL. Success sets the session cookie and 303s to the default
 * landing page (the site's `no-referrer` policy hides the login page's return
 * path); failure 303s back to the login page with an error code only
 * (`too_many_attempts` when the backend rate-limited it).
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!isSameOriginPost(request)) {
    return new NextResponse(null, { status: HTTP_FORBIDDEN });
  }
  const form = await request.formData().catch(() => null);
  const email = form?.get(FIELD_EMAIL);
  const password = form?.get(FIELD_PASSWORD);
  if (typeof email !== "string" || typeof password !== "string") {
    return seeOther(failedLoginPath(LOGIN_ERROR_INVALID_CREDENTIALS));
  }
  if (!email || !password) {
    return seeOther(failedLoginPath(LOGIN_ERROR_INVALID_CREDENTIALS));
  }

  const result = await signIn(email, password).catch(() => INVALID_CREDENTIALS);
  if ("error" in result) return seeOther(failedLoginPath(result.error));

  const response = seeOther(DEFAULT_LOGIN_REDIRECT);
  setAccessTokenCookie(response, result.token, request);
  return response;
}
