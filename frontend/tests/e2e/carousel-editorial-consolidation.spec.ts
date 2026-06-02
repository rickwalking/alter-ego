import { test, expect, type APIRequestContext } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

const BACKEND_BASE_URL =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

async function authHeaders(
  request: APIRequestContext,
): Promise<Record<string, string>> {
  const email = process.env.PLAYWRIGHT_E2E_EMAIL;
  const password = process.env.PLAYWRIGHT_E2E_PASSWORD;
  if (!email || !password) {
    return {};
  }

  const tokenResponse = await request.post(`${BACKEND_BASE_URL}/api/auth/token`, {
    form: {
      username: email,
      password,
    },
  });
  if (!tokenResponse.ok()) {
    return {};
  }
  const tokenPayload = (await tokenResponse.json()) as { access_token?: string };
  if (!tokenPayload.access_token) {
    return {};
  }
  return { Authorization: `Bearer ${tokenPayload.access_token}` };
}

test.describe("Carousel editorial consolidation E2E", () => {
  test("legacy stream and generate endpoints are removed", async ({ request }, testInfo) => {
    const headers = await authHeaders(request);
    if (!headers.Authorization) {
      testInfo.skip(
        true,
        "Set PLAYWRIGHT_E2E_EMAIL and PLAYWRIGHT_E2E_PASSWORD to verify legacy routes return 404",
      );
    }

    const projectId = "00000000-0000-0000-0000-000000000001";

    const streamResponse = await request.get(
      `${BACKEND_BASE_URL}/api/carousels/${projectId}/stream`,
      { headers },
    );
    const generateResponse = await request.post(
      `${BACKEND_BASE_URL}/api/carousels/${projectId}/generate`,
      {
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
        data: { sources: [] },
      },
    );

    expect([404, 410]).toContain(streamResponse.status());
    expect([404, 410]).toContain(generateResponse.status());
  });

  test("frontend api constants exclude legacy carousel stream routes", async () => {
    const apiConstantsPath = path.resolve(
      process.cwd(),
      "src/constants/api.ts",
    );
    const source = readFileSync(apiConstantsPath, "utf8");
    expect(source).not.toContain("CAROUSEL_STREAM");
    expect(source).not.toContain("CAROUSEL_GENERATE");
    expect(source).not.toContain("CAROUSEL_STATUS");
    expect(source).not.toContain("CAROUSEL_RESUME");
    expect(source).toContain("CAROUSEL_WORKFLOW_STREAM");
  });

  test("create workspace route requires authentication", async ({ page }) => {
    await page.goto("/dashboard/create/00000000-0000-0000-0000-000000000001");
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Editorial workflow API (authenticated)", () => {
  test.beforeEach(async (_context, testInfo) => {
    if (!process.env.PLAYWRIGHT_E2E_EMAIL || !process.env.PLAYWRIGHT_E2E_PASSWORD) {
      testInfo.skip(
        true,
        "Set PLAYWRIGHT_E2E_EMAIL and PLAYWRIGHT_E2E_PASSWORD for authenticated workflow E2E",
      );
    }
  });

  test("workflow start pauses at research gate", async ({ request }) => {
    const headers = await authHeaders(request);
    expect(headers.Authorization).toBeTruthy();

    const createResponse = await request.post(`${BACKEND_BASE_URL}/api/carousels`, {
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      data: {
        topic: "Playwright workflow",
        audience: "Developers",
        niche: "AI",
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const project = (await createResponse.json()) as { id: string };

    const startResponse = await request.post(
      `${BACKEND_BASE_URL}/api/carousels/${project.id}/workflow/start`,
      {
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
        data: {
          topic: "Playwright workflow",
          audience: "Developers",
          brief: "Validate editorial workflow start gate",
          sources: [],
        },
      },
    );

    expect(startResponse.ok()).toBeTruthy();
    const state = (await startResponse.json()) as {
      current_phase?: string;
      phase_status?: string;
    };
    expect(state.current_phase).toBe("research");
    expect(state.phase_status).toBe("awaiting_human");
  });
});
