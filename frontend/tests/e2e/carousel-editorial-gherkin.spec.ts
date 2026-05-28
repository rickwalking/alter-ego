/**
 * Playwright E2E — carousel editorial consolidation (Gherkin).
 *
 * Feature: frontend/tests/features/carousel_editorial_consolidation.feature
 *
 * Prerequisites:
 *   docker exec alter-ego-backend-1 uv run python scripts/seed_e2e_carousel_fixtures.py
 *   PLAYWRIGHT_E2E_EMAIL=admin@alterego.app PLAYWRIGHT_E2E_PASSWORD='TestPass123!'
 */

import { test, expect, type Page, type Browser } from "@playwright/test";
import { E2E_FIXTURES } from "./fixtures/carousel-e2e-ids";
import {
  buildOutlineReviewRequiredPayload,
  emitWorkflowSseEvent,
  installWorkflowSseTestBridge,
} from "./helpers/workflow-sse-test-bridge";

const UNAUTHENTICATED_STORAGE = { cookies: [] as [], origins: [] as [] };

async function newGuestContext(browser: Browser) {
  return browser.newContext({ storageState: UNAUTHENTICATED_STORAGE });
}

/** Hard reload so Docker rebuilds do not serve stale client chunks. */
async function openCreateWorkspace(page: Page, projectId: string): Promise<void> {
  await page.goto(`/create/${projectId}`);
  await page.waitForLoadState("domcontentloaded");
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Carousel Workspace" })).toBeVisible({
    timeout: 15_000,
  });
}


test.describe("Carousel editorial consolidation — browser E2E", () => {
  // Scenario: Research gate shows findings and feedback composer
  test("research gate shows findings and feedback composer", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.research);

    await expect(page.getByText("Research findings")).toBeVisible();
    await expect(page.getByText("Researchers found 3,800 internal repositories exposed")).toBeVisible();
    await expect(page.locator("#editorial-feedback")).toBeVisible();
    await expect(page.getByRole("button", { name: "Approve Phase" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Request revision" })).toBeVisible();
  });

  // Scenario: Mount hydrates workflow state once then opens SSE (@cp-sse-primary)
  test("mount hydrates workflow state once then opens SSE", async ({ page }) => {
    const stateRequests: string[] = [];
    const streamRequests: string[] = [];

    await page.route("**/workflow/state", async (route) => {
      stateRequests.push(route.request().url());
      await route.continue();
    });
    await page.route("**/workflow/stream", async (route) => {
      streamRequests.push(route.request().url());
      await route.continue();
    });

    await openCreateWorkspace(page, E2E_FIXTURES.research);
    await expect(page.getByText("Research findings")).toBeVisible({ timeout: 15_000 });

    expect(stateRequests.length).toBeGreaterThanOrEqual(1);
    expect(stateRequests.length).toBeLessThanOrEqual(2);
    expect(streamRequests.length).toBeGreaterThanOrEqual(1);
  });

  // Scenario: Request revision requires feedback text
  test("request revision requires feedback text at outline gate", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.outline);

    await page.getByRole("button", { name: "Request revision" }).click();
    await expect(
      page.getByText("Feedback is required when requesting a revision."),
    ).toBeVisible();
    await expect(page.getByText("awaiting_human")).toBeVisible();
  });

  // Scenario: Content approve disabled when persona score below threshold
  test("content approve disabled when persona score below threshold", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.contentPersona);

    const approve = page.getByRole("button", { name: "Approve Phase" });
    await expect(approve).toBeDisabled();
    await expect(
      page.getByText("Persona voice match is below the required threshold"),
    ).toBeVisible();
    await expect(page.locator("#editorial-feedback")).toBeVisible();
  });

  // Scenario: Final review tab shows carousel blog caption and quality scores
  test("final review tabs show carousel blog caption and quality scores", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.finalReview);

    await expect(page.getByRole("tab", { name: "Carousel" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Blog" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Caption" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Quality" })).toBeVisible();

    await page.getByRole("tab", { name: "Blog" }).click();
    await expect(page.getByText("E2E Published Blog")).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`/create/${E2E_FIXTURES.finalReview}`));

    await page.getByRole("tab", { name: "Quality" }).click();
    await expect(page.getByText("voice match")).toBeVisible();
    await expect(page.getByText("88")).toBeVisible();
  });

  // Scenario: No progress polling loop at awaiting_human gate
  test("no legacy stream polling at design awaiting_human gate", async ({ page }) => {
    const requests: string[] = [];
    page.on("request", (req) => {
      const url = req.url();
      if (url.includes("/api/carousels/")) {
        requests.push(url);
      }
    });

    await openCreateWorkspace(page, E2E_FIXTURES.designGate);
    await page.waitForTimeout(10_000);

    const legacyStream = requests.filter(
      (url) => url.includes("/stream") && !url.includes("/workflow/stream"),
    );
    expect(legacyStream).toHaveLength(0);

    const statePolls = requests.filter((url) => url.includes("/workflow/state"));
    expect(statePolls.length).toBeLessThanOrEqual(2);

    await expect(page.getByText("awaiting_human")).toBeVisible();
    await expect(page.getByText("Design system applied")).toBeVisible();
  });

  // Scenario: Progress strip active during in_progress only
  test("progress message visible during images in_progress", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.imagesProgress);

    await expect(page.getByText("Generating slide 5 of 10")).toBeVisible();
  });

  // Scenario: Reload restores persisted phase progress snapshot
  test("reload restores persisted image progress snapshot", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.imagesProgress);
    await expect(page.getByText("Generating slide 5 of 10")).toBeVisible();

    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByText("Generating slide 5 of 10")).toBeVisible();
  });

  // Scenario: Admin sees 404 on public blog page for draft carousel
  test("admin sees 404 on public blog for draft carousel", async ({ page }) => {
    await page.goto(`/blog/${E2E_FIXTURES.outline}`);
    await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Page Not Found" })).toBeVisible();
  });

  // Scenario: Editor previews draft blog inside create workspace
  test("editor previews draft blog inside create workspace", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.finalReview);

    await expect(page.getByRole("heading", { name: "Draft blog preview" })).toBeVisible();
    await page.getByRole("button", { name: "Load preview" }).click();
    await expect(page.getByText("E2E Published Blog")).toBeVisible();
    expect(page.url()).toContain(`/create/${E2E_FIXTURES.finalReview}`);
    expect(page.url()).not.toContain("/blog/");
  });

  // Scenario: Public blog page has no admin publish panel
  test("public blog page has no admin publish panel", async ({ page }) => {
    await page.goto(`/blog/${E2E_FIXTURES.publicBlog}`);
    await expect(page.getByText("E2E Published Blog")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Publish to site" })).toHaveCount(0);
    await expect(page.getByText("Publish to Instagram")).toHaveCount(0);
  });

  // Scenario: Publish panel appears after final review approval
  test("publish panel shows Instagram LinkedIn and Publish to site when approved", async ({
    page,
  }) => {
    await page.goto(`/create/${E2E_FIXTURES.approvedPublish}/publish`);
    await page.reload({ waitUntil: "domcontentloaded" });

    await expect(page.getByRole("tab", { name: "Instagram" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "LinkedIn" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Publish to site" })).toBeVisible();
  });

  // Scenario: Publish panel gated before approval
  test("publish panel hides Publish to site before final approval", async ({ page }) => {
    await page.goto(`/create/${E2E_FIXTURES.outline}/publish`);
    await page.reload({ waitUntil: "domcontentloaded" });

    await expect(page.getByText("Complete final review in the create workspace")).toBeVisible();
    await expect(page.getByRole("button", { name: "Publish to site" })).toHaveCount(0);
    await expect(page.getByRole("tab", { name: "Instagram" })).toBeVisible();
  });

  // Scenario: Send final review back to content phase (UI controls)
  test("final review exposes send-back phase selector and revision flow", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.finalReview);

    await expect(page.getByLabel("Send back to phase")).toBeVisible();
    await page.getByLabel("Send back to phase").selectOption("content");
    await page.locator("#editorial-feedback").fill("Intro slide needs a personal anecdote");
    await expect(page.getByRole("button", { name: "Request revision" })).toBeEnabled();
  });

  // Scenario: Create workspace requires authentication
  test("create workspace requires authentication", async ({ browser }) => {
    const context = await newGuestContext(browser);
    const page = await context.newPage();
    await page.goto(`/create/${E2E_FIXTURES.research}`);
    await expect(page).toHaveURL(/\/login/);
    await context.close();
  });

  // Scenario: Outline revise structured reorder (CP-017) — expected fail until implemented
  test("outline reorder UI is not yet available (CP-017 deferred)", async ({ page }) => {
    await openCreateWorkspace(page, E2E_FIXTURES.outline);

    const draggable = page.locator('[draggable="true"]');
    const reorderControls = page.locator(
      '[data-testid*="reorder"], [aria-label*="Reorder"], button:has-text("Move")',
    );
    await expect(draggable).toHaveCount(0);
    await expect(reorderControls).toHaveCount(0);
  });
});

test.describe("Resume gap — @cp-resume-gap", () => {
  test.beforeEach(async ({ page }) => {
    await installWorkflowSseTestBridge(page);
  });

  const OUTLINE_SLIDES = [
    {
      slide_index: 1,
      title: "Hook slide",
      key_points: ["Opening hook"],
      visual_direction: "Bold opener",
    },
  ];

  // Scenario: Outline artifacts appear without manual page refresh after research approval
  test("@cp-resume-gap outline artifacts appear without manual refresh", async ({ page }) => {
    await page.route("**/workflow/resume", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({
          accepted: true,
          project_id: E2E_FIXTURES.research,
          current_phase: "research",
          phase_status: "in_progress",
          lock_version: 2,
        }),
      });
    });

    await openCreateWorkspace(page, E2E_FIXTURES.research);
    await page.getByRole("button", { name: "Approve Phase" }).click();
    await emitWorkflowSseEvent(
      page,
      "review_required",
      buildOutlineReviewRequiredPayload(E2E_FIXTURES.research, OUTLINE_SLIDES),
    );

    await expect(page.getByText("Hook slide")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Outline for review")).toBeVisible();
    expect(page.url()).toContain(`/create/${E2E_FIXTURES.research}`);
  });

  // Scenario: Resume transport failure does not show error banner when workflow recovers
  test("@cp-resume-gap transport failure does not show error banner during recovery", async ({
    page,
  }) => {
    let pollCount = 0;

    await page.route("**/workflow/resume", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "proxy timeout" }),
      });
    });

    await page.route("**/workflow/state", async (route) => {
      pollCount += 1;
      if (pollCount < 3) {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project_id: E2E_FIXTURES.research,
          current_phase: "outline",
          phase_status: "awaiting_human",
          research_findings: [
            {
              source: "E2E security report",
              summary: "Synthetic research findings for Playwright E2E validation.",
            },
          ],
          outline: OUTLINE_SLIDES,
          slide_drafts: [],
          lock_version: 2,
        }),
      });
    });

    await openCreateWorkspace(page, E2E_FIXTURES.research);
    await page.getByRole("button", { name: "Approve Phase" }).click();

    await expect(page.getByText("Hook slide")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Failed to resume editorial workflow")).toHaveCount(0);
  });
});

test.describe("Async resume — @cp-async-resume", () => {
  test.beforeEach(async ({ page }) => {
    await installWorkflowSseTestBridge(page);
  });

  const OUTLINE_SLIDES = [
    {
      slide_index: 1,
      title: "Hook slide",
      key_points: ["Opening hook"],
    },
  ];

  // Scenario: Approve clears loading via SSE not resume HTTP response
  test("@cp-async-resume approve returns 202 without interval state polling", async ({ page }) => {
    const stateRequests: string[] = [];

    page.on("request", (request) => {
      if (request.url().includes("/workflow/state")) {
        stateRequests.push(request.url());
      }
    });

    await page.route("**/workflow/resume", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      const started = Date.now();
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({
          accepted: true,
          project_id: E2E_FIXTURES.research,
          current_phase: "research",
          phase_status: "in_progress",
          lock_version: 2,
        }),
      });
      expect(Date.now() - started).toBeLessThan(2_000);
    });

    await openCreateWorkspace(page, E2E_FIXTURES.research);
    const baselineStatePolls = stateRequests.length;

    await page.getByRole("button", { name: "Approve Phase" }).click();
    await emitWorkflowSseEvent(
      page,
      "review_required",
      buildOutlineReviewRequiredPayload(E2E_FIXTURES.research, OUTLINE_SLIDES),
    );
    await expect(page.getByText("Hook slide")).toBeVisible({ timeout: 15_000 });

    expect(stateRequests.length - baselineStatePolls).toBeLessThanOrEqual(1);
  });

  // Scenario: Double-click approve does not enqueue duplicate background jobs
  test("@cp-async-resume double-click sends at most one successful resume", async ({ page }) => {
    const resumeStatuses: number[] = [];

    await page.route("**/workflow/resume", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      resumeStatuses.push(202);
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({
          accepted: true,
          project_id: E2E_FIXTURES.outline,
          current_phase: "outline",
          phase_status: "in_progress",
          lock_version: 2,
        }),
      });
    });

    await openCreateWorkspace(page, E2E_FIXTURES.outline);
    const approveButton = page.getByRole("button", { name: "Approve Phase" });
    await approveButton.dblclick();

    await expect.poll(() => resumeStatuses.length).toBe(1);
    expect(resumeStatuses).toEqual([202]);
    await expect(approveButton).toBeDisabled();
  });
});

test.describe("Publish to site — full browser flow", () => {
  test("publish to site makes public blog accessible without auth", async ({
    page,
    browser,
  }) => {
    await page.goto(`/create/${E2E_FIXTURES.approvedPublish}/publish`);
    await page.reload({ waitUntil: "domcontentloaded" });

    const publishButton = page.getByRole("button", { name: "Publish to site" });
    await expect(publishButton).toBeVisible({ timeout: 15_000 });
    await publishButton.click();
    await expect(page.getByText(/public on the blog/i)).toBeVisible({ timeout: 15_000 });

    const guestContext = await newGuestContext(browser);
    const guestPage = await guestContext.newPage();
    await guestPage.goto(`/blog/${E2E_FIXTURES.approvedPublish}`);
    await expect(guestPage.getByText("E2E Published Blog")).toBeVisible({ timeout: 15_000 });
    await guestContext.close();
  });
});
