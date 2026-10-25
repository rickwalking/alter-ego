import { it, expect, vi, beforeEach, describe } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { HTTP_METHODS } from "@/constants/api";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import {
  PHOTOS,
  PROJECT,
  PROMPT,
  generation,
  list,
  postBodies,
  renderPanel,
  routeApi,
} from "./cover-generate-panel.test-utils";

/**
 * Gherkin: frontend/tests/features/cover-generation-text-upload-ae0551.feature
 * (backend contract: backend/tests/features/cover_generation_text_ae0551.feature).
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
const FILE = new File(["png"], "me.png", { type: "image/png" });

function uploadInput(): HTMLInputElement {
  const label = screen.getByText(/^upload/);
  const input = label.querySelector("input");
  if (!input) {
    throw new Error("no file input");
  }
  return input;
}

beforeEach(() => {
  mockApiCall.mockReset();
});

describe("CoverGeneratePanel without photos", () => {
  /** Scenario: The owner generates a cover without photos */
  it("confirms without claiming photos and posts no photo ids", async () => {
    routeApi([list(), list({ generations: [generation("pending")] })]);
    const { user } = renderPanel();
    await screen.findByText(/^usage/);
    await user.type(screen.getByRole("textbox"), PROMPT);

    await user.click(screen.getByRole("button", { name: "action" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog.textContent).toContain("confirm.textTitle");
    expect(dialog.textContent).toContain("confirm.textBody");
    expect(dialog.textContent).not.toContain("confirm.body");
    expect(dialog.textContent).toContain('"carouselCap":4');
    await user.click(screen.getByRole("button", { name: "confirm.action" }));

    await waitFor(() =>
      expect(postBodies()).toEqual([
        { photo_ids: [], prompt: PROMPT, confirmed: true },
      ]),
    );
  });

  /** Scenario: The owner generates a cover without photos */
  it("keeps the photo wording when a photo is ticked", async () => {
    routeApi([list()]);
    const { user } = renderPanel();
    await screen.findByText(/^usage/);
    await user.click(screen.getByLabelText(/photoLabel \{"number":1\}/));
    await user.type(screen.getByRole("textbox"), PROMPT);

    await user.click(screen.getByRole("button", { name: "action" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog.textContent).toContain("confirm.title");
    expect(dialog.textContent).toContain("confirm.body");
    expect(dialog.textContent).not.toContain("confirm.textBody");
  });
});

describe("CoverGeneratePanel upload", () => {
  /** Scenario: An uploaded photo is added to the library and ticked */
  it("uploads the file, refreshes the options and ticks the new photo", async () => {
    routeApi([list()]);
    const upload = vi.fn().mockResolvedValue("new-photo");
    const { user, client, setPhotos } = renderPanel(PHOTOS, undefined, upload);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await screen.findByText(/^usage/);

    await user.upload(uploadInput(), FILE);

    expect(upload).toHaveBeenCalledWith(FILE);
    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({
        queryKey: ["carousel-cover-options", PROJECT],
      }),
    );
    setPhotos([...PHOTOS, { asset_id: "new-photo", source: "library" }]);
    await user.type(screen.getByRole("textbox"), PROMPT);
    await user.click(screen.getByRole("button", { name: "action" }));
    await user.click(
      await screen.findByRole("button", { name: "confirm.action" }),
    );
    await waitFor(() =>
      expect(postBodies()).toEqual([
        { photo_ids: ["new-photo"], prompt: PROMPT, confirmed: true },
      ]),
    );
  });

  /** Scenario: An uploaded photo is added to the library and ticked */
  it("does not tick an upload past three photos", async () => {
    routeApi([list()]);
    const upload = vi.fn().mockResolvedValue("new-photo");
    const { user } = renderPanel(PHOTOS, undefined, upload);
    await screen.findByText(/^usage/);
    for (const number of [1, 2, 3]) {
      await user.click(
        screen.getByLabelText(new RegExp(`"number":${number}}`)),
      );
    }

    await user.upload(uploadInput(), FILE);
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

  /** Scenario: An invalid file shows the library upload error */
  it("shows the library upload error when the file is refused", async () => {
    routeApi([list()]);
    const upload = vi.fn().mockRejectedValue(new ApiError(422, "bad type"));
    const { user } = renderPanel(PHOTOS, undefined, upload);
    await screen.findByText(/^usage/);

    await user.upload(uploadInput(), FILE);

    expect((await screen.findByRole("alert")).textContent).toBe("uploadFailed");
    expect(
      mockApiCall.mock.calls.some(
        ([, , init]) => init?.method === HTTP_METHODS.POST,
      ),
    ).toBe(false);
  });

  /** Scenario: The panel works with an empty library */
  it("offers the upload and the prompt with an empty library", async () => {
    routeApi([list()]);
    renderPanel([], undefined, vi.fn().mockResolvedValue("new-photo"));
    await screen.findByText(/^usage/);

    expect(uploadInput().disabled).toBe(false);
    expect(screen.getByRole("textbox")).toBeTruthy();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  /** Scenario: An uploaded photo is added to the library and ticked */
  it("holds the generate action while a photo is uploading", async () => {
    routeApi([list()]);
    const pending: ((assetId: string) => void)[] = [];
    const upload = vi.fn(
      () =>
        new Promise<string>((resolve) => {
          pending.push(resolve);
        }),
    );
    const { user } = renderPanel(PHOTOS, undefined, upload);
    await screen.findByText(/^usage/);
    await user.type(screen.getByRole("textbox"), PROMPT);
    const action = screen.getByRole("button", { name: "action" });

    await user.upload(uploadInput(), FILE);

    expect(await screen.findByText("uploading")).toBeTruthy();
    expect(action).toHaveProperty("disabled", true);
    pending[0]?.("new-photo");
    await waitFor(() => expect(action).toHaveProperty("disabled", false));
  });

  /** Scenario: The panel works with an empty library */
  it("offers no upload when the page gives no library upload", async () => {
    routeApi([list()]);
    renderPanel([]);
    await screen.findByText(/^usage/);

    expect(screen.queryByText("upload")).toBeNull();
  });
});

describe("cover generation text and upload copy", () => {
  /** Scenario: The owner generates a cover without photos */
  /** Scenario: An invalid file shows the library upload error */
  it.each([
    ["pt", pt],
    ["en", en],
  ])("the %s copy names no photo and reuses the upload error", (_l, m) => {
    const generate = m.publish.coverPicker.generate;
    expect(generate.confirm.textTitle).toContain("OpenAI (ChatGPT)");
    expect(generate.confirm.textBody).toContain("{carouselCap}");
    expect(generate.confirm.textBody).toContain("{monthCap}");
    expect(m.create.photo.uploadFailed).toContain("5 MB");
  });
});
