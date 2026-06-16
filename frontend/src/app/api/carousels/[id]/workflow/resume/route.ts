import { NextRequest, NextResponse } from "next/server";
import {
  CONTENT_TYPES,
  HTTP_METHODS,
  resolveBackendUrl,
} from "@/constants/api";

// Allow long-running LLM resume calls through the Next.js proxy.
// Next.js route segment config must be a statically-analyzable literal
// (it cannot reference an imported constant), so this 300s value stays inline.
export const maxDuration = 300;

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await context.params;
  const backendUrl = resolveBackendUrl();
  const body = await request.text();
  const cookie = request.headers.get("cookie") ?? "";

  const response = await fetch(
    `${backendUrl}/api/carousels/${id}/workflow/resume`,
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
