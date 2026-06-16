import { NextRequest, NextResponse } from "next/server";

import {
  CONTENT_TYPES,
  HTTP_METHODS,
  resolveBackendUrl,
} from "@/constants/api";
import { setAccessTokenCookie } from "@/lib/auth-cookie";

interface TokenPayload {
  access_token?: string;
}

/**
 * Login BFF: proxy credentials to the backend and set access_token on the
 * frontend host so Next.js middleware can read it (rewrites alone may drop
 * Set-Cookie on some setups).
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const backendUrl = resolveBackendUrl();
  const body = await request.text();

  const backendResponse = await fetch(`${backendUrl}/api/auth/token`, {
    method: HTTP_METHODS.POST,
    headers: {
      "Content-Type": request.headers.get("content-type") ?? CONTENT_TYPES.JSON,
    },
    body,
  });

  const responseBody = await backendResponse.text();
  const nextResponse = new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: {
      "Content-Type":
        backendResponse.headers.get("content-type") ?? CONTENT_TYPES.JSON,
    },
  });

  if (!backendResponse.ok) {
    return nextResponse;
  }

  let payload: TokenPayload;
  try {
    payload = JSON.parse(responseBody) as TokenPayload;
  } catch {
    return nextResponse;
  }

  if (payload.access_token) {
    setAccessTokenCookie(nextResponse, payload.access_token, request);
  }

  return nextResponse;
}
