import { it, expect, vi, beforeEach, describe } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { ApiError } from "@/lib/api-client";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import {
  PHOTOS,
  PROMPT,
  generation,
  list,
  postBodies,
  renderPanel,
  routeApi,
} from "./cover-generate-panel.test-utils";

/**
 * Gherkin: frontend/tests/features/cover-panel-follow-up-ae0554.feature.
 */

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(
    (scope?: string) => (key: string, values?: Record<string, unknown>) => {
      const full = scope === "create.photo" ? `photo.${key}` : key;
      return values ? `${full} ${JSON.stringify(values)}` : full;
    },
  ),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiCall: vi.fn() };
});

import { apiCall } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);
const FILE = new File(["png"], "me.png", { type: "image/png" });
const NEW_PHOTO = { asset_id: "new-photo", source: "library" as const };

function uploadInput(): HTMLInputElement {
  const input = screen.getByText(/^upload/).querySelector("input");
  if (!input) {
    throw new Error("no file input");
  }
  return input;
}

beforeEach(() => {
  mockApiCall.mockReset();
});

describe("cover panel for someone who is not the owner", () => {
  /** Scenario: A viewer who is not the owner sees no upload or generate control */
  it("shows only the not-owner note and uploads nothing", async () => {
    mockApiCall.mockRejectedValue(new ApiError(403, "forbidden"));
    const upload = vi.fn().mockResolvedValue("x");
    renderPanel(PHOTOS, undefined, upload);

    expect((await screen.findByRole("note")).textContent).toBe(
      "errors.notOwner",
    );
    expect(screen.queryByText(/^upload/)).toBeNull();
    expect(screen.queryByRole("button", { name: "action" })).toBeNull();
    expect(upload).not.toHaveBeenCalled();
  });

  /** Scenario: No control is shown while the generation list loads */
  it("shows no upload or generate control while the list loads", () => {
    mockApiCall.mockReturnValue(new Promise(() => undefined));
    renderPanel(PHOTOS, undefined, vi.fn());

    expect(screen.queryByText(/^upload/)).toBeNull();
    expect(screen.queryByRole("button", { name: "action" })).toBeNull();
  });
});

describe("upload errors by cause", () => {
  /** Scenario: An upload failure says its cause */
  it.each([
    [new ApiError(429, "slow down"), "uploadErrors.rateLimited"],
    [new TypeError("Failed to fetch"), "uploadErrors.network"],
    [new ApiError(503, "down"), "uploadErrors.server"],
    [new ApiError(413, "too large"), "photo.uploadFailed"],
    [new ApiError(422, "bad type"), "photo.uploadFailed"],
  ])("explains %s", async (error, message) => {
    routeApi([list()]);
    const upload = vi.fn().mockRejectedValue(error);
    const { user } = renderPanel(PHOTOS, undefined, upload);
    await screen.findByText(/^usage/);

    await user.upload(uploadInput(), FILE);

    expect((await screen.findByRole("alert")).textContent).toBe(message);
  });

  /** Scenario: An upload failure says its cause */
  it.each([
    ["pt", pt],
    ["en", en],
  ])("the %s copy has one uploadFailed and a message per cause", (_l, m) => {
    const generate: Record<string, unknown> = m.publish.coverPicker.generate;
    expect(generate.uploadFailed).toBeUndefined();
    expect(m.create.photo.uploadFailed).toBeTruthy();
    const causes = m.publish.coverPicker.generate.uploadErrors;
    expect(Object.keys(causes).sort((x, y) => x.localeCompare(y))).toEqual([
      "network",
      "rateLimited",
      "server",
    ]);
  });
});

describe("generation list polling", () => {
  /** Scenario: The generation list polls only while a generation runs */
  it("does not poll without a pending generation", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      routeApi([list()]);
      renderPanel();
      await screen.findByText(/^usage/);
      const reads = mockApiCall.mock.calls.length;

      await vi.advanceTimersByTimeAsync(20000);

      expect(mockApiCall.mock.calls.length).toBe(reads);
    } finally {
      vi.useRealTimers();
    }
  });

  /** Scenario: The generation list polls only while a generation runs */
  it("polls while a generation is pending", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      routeApi([list({ generations: [generation("pending")] })]);
      renderPanel();
      await screen.findByText("pending");
      const reads = mockApiCall.mock.calls.length;

      await vi.advanceTimersByTimeAsync(9000);

      expect(mockApiCall.mock.calls.length).toBeGreaterThan(reads);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("an uploaded photo is ticked once listed", () => {
  /** Scenario: An uploaded photo is ticked once it is listed */
  it("waits for the refetched options before ticking the upload", async () => {
    routeApi([list()]);
    const upload = vi.fn().mockResolvedValue(NEW_PHOTO.asset_id);
    const { user, setPhotos } = renderPanel(PHOTOS, undefined, upload);
    await screen.findByText(/^usage/);
    await user.click(screen.getByLabelText(/"number":1}/));
    await user.click(screen.getByLabelText(/"number":2}/));

    await user.upload(uploadInput(), FILE);
    await waitFor(() => expect(upload).toHaveBeenCalled());
    await user.click(screen.getByLabelText(/"number":3}/));
    setPhotos([...PHOTOS, NEW_PHOTO]);

    expect(screen.getByLabelText(/"number":5}/)).toHaveProperty(
      "checked",
      false,
    );
    await user.type(screen.getByRole("textbox"), PROMPT);
    await user.click(screen.getByRole("button", { name: "action" }));
    await user.click(
      await screen.findByRole("button", { name: "confirm.action" }),
    );
    await waitFor(() =>
      expect(postBodies()).toEqual([
        { photo_ids: ["a", "b", "c"], prompt: PROMPT, confirmed: true },
      ]),
    );
  });

  /** Scenario: An uploaded photo is ticked once it is listed */
  it("ticks the upload when the options list it", async () => {
    routeApi([list()]);
    const upload = vi.fn().mockResolvedValue(NEW_PHOTO.asset_id);
    const { user, setPhotos } = renderPanel(PHOTOS, undefined, upload);
    await screen.findByText(/^usage/);

    await user.upload(uploadInput(), FILE);
    await waitFor(() => expect(upload).toHaveBeenCalled());
    setPhotos([...PHOTOS, NEW_PHOTO]);

    await waitFor(() =>
      expect(screen.getByLabelText(/"number":5}/)).toHaveProperty(
        "checked",
        true,
      ),
    );
  });
});
