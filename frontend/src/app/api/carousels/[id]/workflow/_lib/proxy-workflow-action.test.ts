/**
 * Shared carousel workflow proxy helper (start/resume routes).
 * Verifies the request is forwarded to the correct backend action with body,
 * content-type, and cookie, and that the backend status + content-type are
 * mirrored back (including the fallback when headers are absent).
 */
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  proxyWorkflowAction,
  proxyWorkflowRead,
  WORKFLOW_ACTIONS,
} from "./proxy-workflow-action";

const BACKEND_BASE = "http://backend.test";

vi.mock("@/constants/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/constants/api")>();
  return { ...actual, resolveBackendUrl: () => BACKEND_BASE };
});

function makeRequest(body: string, contentType?: string): NextRequest {
  const headers = new Headers();
  if (contentType) headers.set("content-type", contentType);
  headers.set("cookie", "session=abc");
  return new NextRequest("http://app.test/api/carousels/c1/workflow/start", {
    method: "POST",
    headers,
    body,
  });
}

function ctx(id: string) {
  return { params: Promise.resolve({ id }) };
}

afterEach(() => vi.restoreAllMocks());

describe("proxyWorkflowAction", () => {
  it("forwards body, content-type, and cookie to the backend action URL", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"ok":true}', {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await proxyWorkflowAction(
      makeRequest('{"a":1}', "application/json"),
      ctx("c1"),
      WORKFLOW_ACTIONS.START,
    );

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe(`${BACKEND_BASE}/api/carousels/c1/workflow/start`);
    expect(init?.method).toBe("POST");
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe(
      "application/json",
    );
    expect((init?.headers as Record<string, string>).Cookie).toBe(
      "session=abc",
    );
    expect(init?.body).toBe('{"a":1}');
    expect(response.status).toBe(200);
    expect(await response.text()).toBe('{"ok":true}');
  });

  it("targets the resume action and mirrors the backend status", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("err", { status: 502 }));

    const response = await proxyWorkflowAction(
      makeRequest("{}", "application/json"),
      ctx("c9"),
      WORKFLOW_ACTIONS.RESUME,
    );

    expect(fetchMock.mock.calls[0]![0]).toBe(
      `${BACKEND_BASE}/api/carousels/c9/workflow/resume`,
    );
    expect(response.status).toBe(502);
  });

  /**
   * A null-body Response carries no content-type header (a string body would
   * auto-set text/plain), which exercises the helper's JSON fallback.
   */
  it("falls back to application/json when request/response omit content-type", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 200 }),
    );

    const response = await proxyWorkflowAction(
      makeRequest("{}"),
      ctx("c2"),
      WORKFLOW_ACTIONS.START,
    );

    expect(response.headers.get("content-type")).toBe("application/json");
  });

  // Scenario: The proxy forwards the retry to the backend
  it("reads a workflow action with the cookie and mirrors the answer", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"can_retry":false}', {
        status: 403,
        headers: { "content-type": "application/problem+json" },
      }),
    );
    const request = new NextRequest(
      "http://app.test/api/carousels/c3/workflow/retry",
      { headers: { cookie: "session=abc" } },
    );

    const response = await proxyWorkflowRead(
      request,
      ctx("c3"),
      WORKFLOW_ACTIONS.RETRY,
    );

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe(`${BACKEND_BASE}/api/carousels/c3/workflow/retry`);
    expect(init?.method).toBe("GET");
    expect((init?.headers as Record<string, string>).Cookie).toBe(
      "session=abc",
    );
    expect(response.status).toBe(403);
    expect(response.headers.get("content-type")).toBe(
      "application/problem+json",
    );
    expect(await response.text()).toBe('{"can_retry":false}');
  });

  // Scenario: The proxy forwards the retry to the backend
  it("reads without a cookie", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 200 }));

    await proxyWorkflowRead(
      new NextRequest("http://app.test/api/carousels/c4/workflow/retry"),
      ctx("c4"),
      WORKFLOW_ACTIONS.RETRY,
    );

    const init = fetchMock.mock.calls[0]![1];
    expect((init?.headers as Record<string, string>).Cookie).toBe("");
  });
});
