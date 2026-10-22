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
} from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { setAccessTokenCookie } from "@/modules/identity";

const HTTP_SEE_OTHER = 303;
const HTTP_FORBIDDEN = 403;
const HEADER_ORIGIN = "origin";
const HEADER_SEC_FETCH_SITE = "sec-fetch-site";
const SAME_ORIGIN_FETCH_SITES: ReadonlySet<string> = new Set([
  "same-origin",
  "none",
]);
const OPAQUE_ORIGIN = "null";
const FIELD_EMAIL = "email";
const FIELD_PASSWORD = "password";
const FAILED_LOGIN_PATH = `${PUBLIC_ROUTE_PATHS.LOGIN}?${new URLSearchParams({
  [LOGIN_ERROR_PARAM]: LOGIN_ERROR_INVALID_CREDENTIALS,
}).toString()}`;

interface TokenPayload {
  access_token?: string;
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

async function accessTokenFor(
  email: string,
  password: string,
): Promise<string | null> {
  const response = await fetch(`${resolveBackendUrl()}/api/auth/token`, {
    method: HTTP_METHODS.POST,
    headers: { "Content-Type": CONTENT_TYPES.JSON },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) return null;
  try {
    const payload = (await response.json()) as TokenPayload;
    return payload.access_token ?? null;
  } catch {
    return null;
  }
}

/**
 * Sign-in for a login form submitted before (or without) JavaScript: the form
 * posts here instead of falling back to a GET that would put the email and
 * password in the URL. Success sets the session cookie and 303s to the default
 * landing page (the site's `no-referrer` policy hides the login page's return
 * path); failure 303s back to the login page with an error code only.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!isSameOriginPost(request)) {
    return new NextResponse(null, { status: HTTP_FORBIDDEN });
  }
  const form = await request.formData().catch(() => null);
  const email = form?.get(FIELD_EMAIL);
  const password = form?.get(FIELD_PASSWORD);
  if (typeof email !== "string" || typeof password !== "string") {
    return seeOther(FAILED_LOGIN_PATH);
  }
  if (!email || !password) return seeOther(FAILED_LOGIN_PATH);

  const token = await accessTokenFor(email, password).catch(() => null);
  if (!token) return seeOther(FAILED_LOGIN_PATH);

  const response = seeOther(DEFAULT_LOGIN_REDIRECT);
  setAccessTokenCookie(response, token, request);
  return response;
}
