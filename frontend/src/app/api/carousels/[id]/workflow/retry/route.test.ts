/** The retry route forwards both verbs to the backend's retry path. */
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

const BACKEND_BASE = "http://backend.test";
const ROUTE_URL = "http://app.test/api/carousels/c1/workflow/retry";

vi.mock("@/constants/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/constants/api")>();
  return { ...actual, resolveBackendUrl: () => BACKEND_BASE };
});

const context = { params: Promise.resolve({ id: "c1" }) };

afterEach(() => vi.restoreAllMocks());

describe("carousel retry route", () => {
  // Scenario: The proxy forwards the retry to the backend
  it("forwards the POST body and mirrors the 202", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response('{"accepted":true}', { status: 202 }));
    const body = '{"expected_version":7}';

    const response = await POST(
      new NextRequest(ROUTE_URL, { method: "POST", body }),
      context,
    );

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe(`${BACKEND_BASE}/api/carousels/c1/workflow/retry`);
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(body);
    expect(response.status).toBe(202);
  });

  // Scenario: The proxy forwards the retry to the backend
  it("forwards the GET and mirrors the capability", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response('{"can_retry":true}', { status: 200 }));

    const response = await GET(new NextRequest(ROUTE_URL), context);

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe(`${BACKEND_BASE}/api/carousels/c1/workflow/retry`);
    expect(init?.method).toBe("GET");
    expect(await response.text()).toBe('{"can_retry":true}');
  });
});
