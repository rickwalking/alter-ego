import { NextRequest, NextResponse } from "next/server";
import {
  CONTENT_TYPES,
  DEFAULT_BACKEND_URL,
  HTTP_METHODS,
} from "@/constants/api";

export const maxDuration = 300;

function resolveBackendUrl(): string {
  return (
    process.env.API_BASE_URL ??
    (process.env.NODE_ENV === "production"
      ? "http://backend:8000"
      : DEFAULT_BACKEND_URL)
  );
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await context.params;
  const backendUrl = resolveBackendUrl();
  const body = await request.text();
  const cookie = request.headers.get("cookie") ?? "";

  const response = await fetch(
    `${backendUrl}/api/carousels/${id}/workflow/start`,
    {
      method: HTTP_METHODS.POST,
      headers: {
        "Content-Type":
          request.headers.get("content-type") ?? CONTENT_TYPES.JSON,
        Cookie: cookie,
      },
      body,
    },
  );

  const responseBody = await response.text();
  return new NextResponse(responseBody, {
    status: response.status,
    headers: {
      "Content-Type":
        response.headers.get("content-type") ?? CONTENT_TYPES.JSON,
    },
  });
}
