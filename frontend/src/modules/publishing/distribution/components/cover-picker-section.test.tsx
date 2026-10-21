import { it, expect, vi, beforeEach, describe } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { CoverPickerSection } from "./cover-picker-section";

// Gherkin: frontend/tests/features/publish-cover-picker-ae0445.feature
// (backend contract: backend/tests/features/carousel_cover_pick_ae0445.feature)

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => {
    const entries: Record<string, string> = {
      title: "Capa (slide 1)",
      description: "Troque a foto do slide 1.",
      offerLabel: "Capa sugerida pelo GrokBot",
      offerShort: "GrokBot",
      current: "Atual",
      switching: "Trocando a capa…",
      success: "Capa trocada.",
      conflict: "Recarregue a página.",
      failed: "Não foi possível trocar a capa.",
      loadFailed: "Não foi possível carregar as fotos.",
      empty: "Nenhuma foto na biblioteca.",
    };
    return (key: string, values?: Record<string, number>) =>
      key === "photoLabel" ? `Foto ${values?.number}` : (entries[key] ?? key);
  }),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiCall: vi.fn() };
});

import { apiCall, ApiError } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);
const PROJECT = "p-1";
const OPTIONS = {
  project_id: PROJECT,
  current_asset_id: "a",
  options: [
    { asset_id: "a", source: "library", kind: "" },
    { asset_id: "b", source: "library", kind: "" },
    { asset_id: "g", source: "offer", kind: "ai_image" },
  ],
};

type Answer = unknown | Error | Promise<unknown>;

function routeApi(options: Answer, pick?: Answer, lockVersion = 7): void {
  mockApiCall.mockImplementation((url: string) => {
    if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE(PROJECT)) {
      return Promise.resolve({ lock_version: lockVersion });
    }
    const answer =
      url === API_ENDPOINTS.CAROUSEL_COVER_OPTIONS(PROJECT) ? options : pick;
    if (answer instanceof Error) {
      return Promise.reject(answer);
    }
    return Promise.resolve(answer);
  });
}

function renderSection(onSwitched = vi.fn()): {
  onSwitched: typeof onSwitched;
} {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }): React.ReactElement {
    return createElement(QueryClientProvider, { client }, children);
  }
  render(<CoverPickerSection projectId={PROJECT} onSwitched={onSwitched} />, {
    wrapper: Wrapper,
  });
  return { onSwitched };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CoverPickerSection", () => {
  // Scenario: The options are thumbnails with the current photo marked
  it("lists the options as radios with the current one checked", async () => {
    routeApi(OPTIONS);
    renderSection();
    const radios = await screen.findAllByRole("radio");
    expect(radios).toHaveLength(3);
    expect(
      screen.getByRole("radiogroup", { name: "Capa (slide 1)" }),
    ).toBeTruthy();
    const current = screen.getByRole("radio", { name: "Foto 1 (Atual)" });
    expect(current.getAttribute("aria-checked")).toBe("true");
    expect(
      screen
        .getByRole("radio", { name: "Foto 2" })
        .getAttribute("aria-checked"),
    ).toBe("false");
    expect(
      screen.getByRole("radio", { name: "Capa sugerida pelo GrokBot" }),
    ).toBeTruthy();
    expect(screen.getByText("GrokBot")).toBeTruthy();
  });

  // Scenario: Choosing another photo switches the cover and refreshes the previews
  // Scenario: The picker is keyboard accessible
  it("switches with the lock version, shows progress, then refreshes", async () => {
    let finish: (value: unknown) => void = () => undefined;
    const pending = new Promise((resolve) => {
      finish = resolve;
    });
    routeApi(OPTIONS, pending);
    const { onSwitched } = renderSection();
    const user = userEvent.setup();
    const second = await screen.findByRole("radio", { name: "Foto 2" });
    second.focus();
    await user.keyboard("{Enter}");

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_COVER(PROJECT),
      expect.anything(),
      {
        method: HTTP_METHODS.PUT,
        body: JSON.stringify({ asset_id: "b", expected_version: 7 }),
      },
    );
    expect(await screen.findByText("Trocando a capa…")).toBeTruthy();
    expect((second as HTMLButtonElement).disabled).toBe(true);

    finish({
      project_id: PROJECT,
      status: "switched",
      current_asset_id: "b",
      artifact_version: "sha256-new",
    });
    expect(await screen.findByText("Capa trocada.")).toBeTruthy();
    expect(onSwitched).toHaveBeenCalledWith("sha256-new");
  });

  it("passes a null artifact version through", async () => {
    routeApi(OPTIONS, {
      project_id: PROJECT,
      status: "switched",
      current_asset_id: "g",
    });
    const { onSwitched } = renderSection();
    await userEvent.click(
      await screen.findByRole("radio", { name: "Capa sugerida pelo GrokBot" }),
    );
    await waitFor(() => expect(onSwitched).toHaveBeenCalledWith(null));
  });

  // Scenario: Choosing the current photo does nothing
  it("ignores a click on the current photo", async () => {
    routeApi(OPTIONS);
    renderSection();
    await userEvent.click(
      await screen.findByRole("radio", { name: "Foto 1 (Atual)" }),
    );
    expect(mockApiCall).toHaveBeenCalledTimes(1);
  });

  // Scenario: A version conflict shows a reload hint
  // AE-0447 Scenario: The pick sends the server's current version, not page state
  it("reads the current lock version right before the switch", async () => {
    routeApi(
      OPTIONS,
      {
        project_id: PROJECT,
        status: "switched",
        current_asset_id: "b",
        artifact_version: "sha256-new",
      },
      11,
    );
    renderSection();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("radio", { name: "Foto 2" }));

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE(PROJECT),
      expect.anything(),
    );
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_COVER(PROJECT),
      expect.anything(),
      {
        method: HTTP_METHODS.PUT,
        body: JSON.stringify({ asset_id: "b", expected_version: 11 }),
      },
    );
  });

  it("shows the reload hint on a 409", async () => {
    routeApi(OPTIONS, new ApiError(409, "version_conflict"));
    renderSection();
    await userEvent.click(await screen.findByRole("radio", { name: "Foto 2" }));
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Recarregue a página.",
    );
  });

  // Scenario: Any other failure is visible
  it("shows the generic failure otherwise", async () => {
    routeApi(OPTIONS, new ApiError(422, "cover_pick_asset_not_allowed"));
    renderSection();
    await userEvent.click(await screen.findByRole("radio", { name: "Foto 2" }));
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Não foi possível trocar a capa.",
    );
  });

  // Scenario: An empty library explains where to add photos
  it("explains an empty library", async () => {
    routeApi({ project_id: PROJECT, current_asset_id: null, options: [] });
    renderSection();
    expect(await screen.findByRole("note")).toBeTruthy();
    expect(screen.queryByRole("radiogroup")).toBeNull();
  });

  // Scenario: The options failing to load is visible
  it("shows a load failure", async () => {
    routeApi(new ApiError(422, "cover_pick_not_pov"));
    renderSection();
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Não foi possível carregar as fotos.",
    );
  });
});
