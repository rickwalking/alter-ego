import { it, expect, vi, beforeEach, describe } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { CoverGeneratePanel } from "./cover-generate-panel";
import { CoverPromptField, generationErrorKey } from "./cover-generate-parts";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";

/**
 * Gherkin: frontend/tests/features/cover-generation-ae0508.feature (backend
 * contract: backend/tests/features/cover_generation_ae0508.feature).
 */

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(
    () => (key: string, values?: Record<string, unknown>) =>
      values ? `${key} ${JSON.stringify(values)}` : key,
  ),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiCall: vi.fn() };
});

import { apiCall, ApiError } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);
const PROJECT = "p-1";
const PHOTOS = [
  { asset_id: "a", source: "library" as const },
  { asset_id: "b", source: "library" as const },
  { asset_id: "c", source: "library" as const },
  { asset_id: "d", source: "library" as const },
];
const PROMPT = "eu num café";

interface ListShape {
  carousel_used: number;
  carousel_cap: number;
  month_used: number;
  month_cap: number;
  carousel_attempts: number;
  carousel_attempt_cap: number;
  month_attempts: number;
  month_attempt_cap: number;
  generations: Record<string, unknown>[];
}

function list(overrides: Partial<ListShape> = {}): ListShape {
  return {
    carousel_used: 1,
    carousel_cap: 4,
    month_used: 3,
    month_cap: 40,
    carousel_attempts: 1,
    carousel_attempt_cap: 12,
    month_attempts: 3,
    month_attempt_cap: 120,
    generations: [],
    ...overrides,
  };
}

function generation(status: string, error_code: string | null = null) {
  return {
    id: `g-${status}`,
    status,
    error_code,
    asset_id: status === "succeeded" ? "made" : null,
    created_at: "2026-10-23T12:00:00Z",
    completed_at: null,
  };
}

function routeApi(
  lists: ListShape[],
  started: unknown = generation("pending"),
): void {
  let call = 0;
  mockApiCall.mockImplementation((url: string, _schema, init?: RequestInit) => {
    if (init?.method === HTTP_METHODS.POST) {
      if (started instanceof Error) {
        return Promise.reject(started);
      }
      return Promise.resolve(started);
    }
    if (url === API_ENDPOINTS.CAROUSEL_COVER_GENERATIONS(PROJECT)) {
      const current = lists[Math.min(call, lists.length - 1)];
      call += 1;
      return Promise.resolve(current);
    }
    return Promise.resolve({});
  });
}

function wrapper(client: QueryClient) {
  function Wrapper({ children }: { children: ReactNode }): React.ReactElement {
    return createElement(QueryClientProvider, { client }, children);
  }
  return Wrapper;
}

function renderPanel(photos = PHOTOS) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const user = userEvent.setup();
  render(createElement(CoverGeneratePanel, { projectId: PROJECT, photos }), {
    wrapper: wrapper(client),
  });
  return { user, client };
}

async function fillForm(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByText(/^usage/);
  await user.click(screen.getByLabelText(/photoLabel \{"number":1\}/));
  await user.type(screen.getByRole("textbox"), PROMPT);
}

function postBodies(): unknown[] {
  return mockApiCall.mock.calls
    .filter(([, , init]) => init?.method === HTTP_METHODS.POST)
    .map(
      ([, , init]) =>
        JSON.parse(
          typeof init?.body === "string" ? init.body : "null",
        ) as unknown,
    );
}

beforeEach(() => {
  mockApiCall.mockReset();
});

describe("CoverGeneratePanel", () => {
  /** Scenario: The owner generates a cover after confirming */
  it("asks for confirmation naming the photos and caps, then posts confirmed", async () => {
    routeApi([list(), list({ generations: [generation("pending")] })]);
    const { user } = renderPanel();
    await fillForm(user);

    await user.click(screen.getByRole("button", { name: "action" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog.textContent).toContain('"count":1');
    expect(dialog.textContent).toContain('"carouselCap":4');
    expect(dialog.textContent).toContain('"monthCap":40');
    expect(postBodies()).toEqual([]);
    await user.click(screen.getByRole("button", { name: "confirm.action" }));

    await waitFor(() =>
      expect(postBodies()).toEqual([
        { photo_ids: ["a"], prompt: PROMPT, confirmed: true },
      ]),
    );
    expect(await screen.findByText("pending")).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  /** Scenario: Cancelling the confirmation sends nothing */
  it("sends nothing when the confirmation is cancelled", async () => {
    routeApi([list()]);
    const { user } = renderPanel();
    await fillForm(user);

    await user.click(screen.getByRole("button", { name: "action" }));
    await user.click(
      await screen.findByRole("button", { name: "confirm.cancel" }),
    );

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(postBodies()).toEqual([]);
  });

  /** Scenario: A reached cap disables the action with the reason */
  it("shows a refused start inside the dialog", async () => {
    const refused = new ApiError(409, "conflict");
    refused.detail = "cover_generation_monthly_cap";
    routeApi([list()], refused);
    const { user } = renderPanel();
    await fillForm(user);

    await user.click(screen.getByRole("button", { name: "action" }));
    await user.click(
      await screen.findByRole("button", { name: "confirm.action" }),
    );

    expect(await screen.findByText("errors.monthlyCap")).toBeTruthy();
    expect(screen.getByRole("dialog")).toBeTruthy();
  });

  /** Scenario: A finished generation appears as a cover option */
  it("refreshes the cover options when a running generation succeeds", async () => {
    routeApi([
      list({ generations: [generation("pending")] }),
      list({ generations: [generation("succeeded")] }),
    ]);
    const { client } = renderPanel();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await screen.findByText("pending");

    await client.refetchQueries({
      queryKey: ["carousel-cover-generations", PROJECT],
    });

    expect(await screen.findByText("succeeded")).toBeTruthy();
    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({
        queryKey: ["carousel-cover-options", PROJECT],
      }),
    );
  });

  /** Scenario: A failed generation can be retried */
  it("shows the failure with a retry that asks again with the same inputs", async () => {
    routeApi([
      list({
        generations: [generation("failed", "cover_generation_bridge_failed")],
      }),
    ]);
    const { user } = renderPanel();
    expect(await screen.findByText("errors.bridge")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "retry" })).toBeNull();
    await fillForm(user);

    await user.click(screen.getByRole("button", { name: "retry" }));
    await user.click(
      await screen.findByRole("button", { name: "confirm.action" }),
    );

    await waitFor(() =>
      expect(postBodies()).toEqual([
        { photo_ids: ["a"], prompt: PROMPT, confirmed: true },
      ]),
    );
  });

  /** Scenario: A failed generation can be retried */
  it("shows the Grok Bot's own message under the reason", async () => {
    routeApi([
      list({
        generations: [
          {
            ...generation("failed", "cover_generation_bridge_failed"),
            error_detail: "content_policy: photos cannot be edited",
          },
        ],
      }),
    ]);
    renderPanel();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("errors.bridge");
    expect(alert.textContent).toContain(
      "content_policy: photos cannot be edited",
    );
  });

  /** Scenario: The action needs a photo and a prompt */
  it("needs a photo and a prompt of three characters", async () => {
    routeApi([list()]);
    const { user } = renderPanel();
    await screen.findByText(/^usage/);
    const action = screen.getByRole("button", { name: "action" });

    expect(action).toHaveProperty("disabled", true);
    await user.type(screen.getByRole("textbox"), "ab");
    await user.click(screen.getByLabelText(/photoLabel \{"number":2\}/));
    expect(action).toHaveProperty("disabled", true);
    await user.type(screen.getByRole("textbox"), "c");
    expect(action).toHaveProperty("disabled", false);
  });

  /** Scenario: A reached cap disables the action with the reason */
  /** Scenario: The attempt ceiling disables the action with the reason */
  it.each([
    [{ carousel_used: 4 }, "blocked.carouselCap"],
    [{ month_used: 40 }, "blocked.monthlyCap"],
    [{ carousel_attempts: 12 }, "blocked.carouselAttempts"],
    [{ month_attempts: 120 }, "blocked.monthlyAttempts"],
  ])("disables the action at a cap (%o)", async (usage, reason) => {
    routeApi([list(usage)]);
    const { user } = renderPanel();
    await fillForm(user);

    expect(screen.getByRole("note").textContent).toBe(reason);
    expect(screen.getByRole("button", { name: "action" })).toHaveProperty(
      "disabled",
      true,
    );
  });

  /** Scenario: At most three photos can be sent */
  it("allows at most three photos", async () => {
    routeApi([list()]);
    const { user } = renderPanel();
    await screen.findByText(/^usage/);
    for (const number of [1, 2, 3]) {
      await user.click(
        screen.getByLabelText(new RegExp(`"number":${number}}`)),
      );
    }

    expect(screen.getByLabelText(/"number":4}/)).toHaveProperty(
      "disabled",
      true,
    );
    await user.click(screen.getByLabelText(/"number":2}/));
    expect(screen.getByLabelText(/"number":4}/)).toHaveProperty(
      "disabled",
      false,
    );
  });

  /** Scenario: The action needs a photo and a prompt */
  it.each([
    [new ApiError(403, "forbidden"), "errors.notOwner"],
    [new ApiError(500, "boom"), "errors.loadFailed"],
  ])("hides the form when the list cannot be read (%s)", async (error, key) => {
    mockApiCall.mockRejectedValue(error);
    renderPanel();

    expect(await screen.findByRole("note")).toHaveProperty("textContent", key);
    expect(screen.queryByRole("button", { name: "action" })).toBeNull();
  });

  /** Scenario: The action needs a photo and a prompt */
  it("renders nothing and reads nothing without library photos", () => {
    routeApi([list()]);
    renderPanel([]);
    expect(screen.queryByRole("button", { name: "action" })).toBeNull();
    expect(mockApiCall).not.toHaveBeenCalled();
  });
});

describe("cover generation copy", () => {
  /** Scenario: The owner generates a cover after confirming */
  /** Scenario: The usage line says when the monthly limit resets */
  it.each([
    ["pt", pt],
    ["en", en],
  ])(
    "the %s copy names OpenAI (ChatGPT), the caps and the 21:00 BRT reset",
    (_lang, messages) => {
      const generate = messages.publish.coverPicker.generate;
      const body = generate.confirm.body;
      expect(generate.usage).toContain("21:00");
      expect(generate.blocked.monthlyCap).toContain("21:00");
      expect(generate.blocked.monthlyAttempts).toContain("120");
      expect(generate.blocked.carouselAttempts).toContain("12");
      expect(body).toContain("OpenAI (ChatGPT)");
      expect(generate.confirm.title).toContain("OpenAI (ChatGPT)");
      expect(body).not.toContain("xAI");
      expect(body).toContain("{carouselCap}");
      expect(body).toContain("{monthCap}");
    },
  );
});

describe("cover generation parts", () => {
  /** Scenario: A failed generation can be retried */
  it("maps known codes and falls back for unknown ones", () => {
    expect(generationErrorKey("cover_generation_interrupted")).toBe(
      "errors.interrupted",
    );
    expect(generationErrorKey("something_else")).toBe("errors.failed");
    expect(generationErrorKey(null)).toBe("errors.failed");
  });

  /** Scenario: The owner generates a cover after confirming */
  it("renders children under the prompt field so they can fill it", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      createElement(
        CoverPromptField,
        { value: "", onChange },
        createElement(
          "button",
          {
            type: "button",
            onClick: () => {
              onChange("ideia");
            },
          },
          "suggestion",
        ),
      ),
    );

    await user.click(screen.getByRole("button", { name: "suggestion" }));

    expect(onChange).toHaveBeenCalledWith("ideia");
  });
});
