import { NextRequest, NextResponse } from "next/server";
import {
  CONTENT_TYPES,
  HTTP_METHODS,
  resolveBackendUrl,
} from "@/constants/api";

/** Carousel workflow actions proxied to the backend (path segment). */
export const WORKFLOW_ACTIONS = {
  START: "start",
  RESUME: "resume",
} as const;

export type WorkflowAction =
  (typeof WORKFLOW_ACTIONS)[keyof typeof WORKFLOW_ACTIONS];

type WorkflowRouteContext = { params: Promise<{ id: string }> };

/**
 * Proxy a carousel workflow action (start/resume) to the backend, forwarding
 * the request body, content-type, and auth cookie, and mirroring the backend
 * status and content-type back. Shared by the start/ and resume/ route
 * handlers so the proxy logic lives in one place (AE-0150).
 */
export async function proxyWorkflowAction(
  request: NextRequest,
  context: WorkflowRouteContext,
  action: WorkflowAction,
): Promise<NextResponse> {
  const { id } = await context.params;
  const backendUrl = resolveBackendUrl();
  const body = await request.text();
  const cookie = request.headers.get("cookie") ?? "";

  const response = await fetch(
    `${backendUrl}/api/carousels/${id}/workflow/${action}`,
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
