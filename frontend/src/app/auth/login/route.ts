import { NextRequest, NextResponse } from "next/server";

import {
  CONTENT_TYPES,
  HTTP_METHODS,
  resolveBackendUrl,
} from "@/constants/api";
import {
  AUTH_LOGIN_REDIRECT_PARAM,
  HTTP_HEADER_HOST,
  LOGIN_ERROR_INVALID_CREDENTIALS,
  LOGIN_ERROR_PARAM,
} from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import {
  sanitizeLoginRedirect,
  setAccessTokenCookie,
} from "@/modules/identity";

const HTTP_SEE_OTHER = 303;
const HTTP_FORBIDDEN = 403;
const HEADER_ORIGIN = "origin";
const HEADER_REFERER = "referer";
const HEADER_SEC_FETCH_SITE = "sec-fetch-site";
const CROSS_SITE = "cross-site";
const FIELD_EMAIL = "email";
const FIELD_PASSWORD = "password";

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

/** A browser form post from another site (login CSRF) is refused. */
function isCrossSite(request: NextRequest): boolean {
  if (request.headers.get(HEADER_SEC_FETCH_SITE) === CROSS_SITE) return true;
  const origin = request.headers.get(HEADER_ORIGIN);
  const host = request.headers.get(HTTP_HEADER_HOST);
  if (!origin || !host) return false;
  try {
    return new URL(origin).host !== host;
  } catch {
    return true;
  }
}

/** The `?redirect=` of the login page the form was posted from. */
function returnPathOf(request: NextRequest): string | null {
  const referer = request.headers.get(HEADER_REFERER);
  if (!referer) return null;
  try {
    return new URL(referer).searchParams.get(AUTH_LOGIN_REDIRECT_PARAM);
  } catch {
    return null;
  }
}

function failedLogin(returnPath: string | null): NextResponse {
  const params = new URLSearchParams({
    [LOGIN_ERROR_PARAM]: LOGIN_ERROR_INVALID_CREDENTIALS,
  });
  if (returnPath) {
    params.set(AUTH_LOGIN_REDIRECT_PARAM, sanitizeLoginRedirect(returnPath));
  }
  return seeOther(`${PUBLIC_ROUTE_PATHS.LOGIN}?${params.toString()}`);
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
 * password in the URL. Success sets the session cookie and 303s to the safe
 * return path; failure 303s back to the login page with an error code only.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  if (isCrossSite(request)) {
    return new NextResponse(null, { status: HTTP_FORBIDDEN });
  }
  const returnPath = returnPathOf(request);
  const form = await request.formData().catch(() => null);
  const email = form?.get(FIELD_EMAIL);
  const password = form?.get(FIELD_PASSWORD);
  if (typeof email !== "string" || typeof password !== "string") {
    return failedLogin(returnPath);
  }
  if (!email || !password) return failedLogin(returnPath);

  const token = await accessTokenFor(email, password).catch(() => null);
  if (!token) return failedLogin(returnPath);

  const response = seeOther(sanitizeLoginRedirect(returnPath));
  setAccessTokenCookie(response, token, request);
  return response;
}
