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
  RETRY: "retry",
} as const;

export type WorkflowAction =
  (typeof WORKFLOW_ACTIONS)[keyof typeof WORKFLOW_ACTIONS];

interface WorkflowRouteContext {
  params: Promise<{ id: string }>;
}

/** Mirror a backend answer's status, body and content-type. */
async function mirrorResponse(response: Response): Promise<NextResponse> {
  const responseBody = await response.text();
  return new NextResponse(responseBody, {
    status: response.status,
    headers: {
      "Content-Type":
        response.headers.get("content-type") ?? CONTENT_TYPES.JSON,
    },
  });
}

/**
 * Proxy a carousel workflow action (start/resume/retry) to the backend, forwarding
 * the request body, content-type, and auth cookie, and mirroring the backend
 * status and content-type back. Shared by the start/ and resume/ route
 * handlers so the proxy logic lives in one place.
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

  return mirrorResponse(response);
}

/**
 * Proxy the read of a workflow action (the retry capability), forwarding the
 * auth cookie and mirroring the backend answer.
 */
export async function proxyWorkflowRead(
  request: NextRequest,
  context: WorkflowRouteContext,
  action: WorkflowAction,
): Promise<NextResponse> {
  const { id } = await context.params;
  const response = await fetch(
    `${resolveBackendUrl()}/api/carousels/${id}/workflow/${action}`,
    {
      method: HTTP_METHODS.GET,
      headers: { Cookie: request.headers.get("cookie") ?? "" },
    },
  );
  return mirrorResponse(response);
}
