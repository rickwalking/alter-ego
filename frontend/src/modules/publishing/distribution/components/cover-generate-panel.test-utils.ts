import { vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { apiCall } from "@/lib/api-client";
import { CoverGeneratePanel } from "./cover-generate-panel";

/**
 * Shared fixtures of the cover generation panel tests: the generation list,
 * an ``apiCall`` router (the test file mocks ``@/lib/api-client``), the
 * rendered panel and the POST bodies sent.
 */
export const PROJECT = "p-1";
export const PHOTOS = [
  { asset_id: "a", source: "library" as const },
  { asset_id: "b", source: "library" as const },
  { asset_id: "c", source: "library" as const },
  { asset_id: "d", source: "library" as const },
];
export const PROMPT = "eu num café";

export interface ListShape {
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

export function list(overrides: Partial<ListShape> = {}): ListShape {
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

export function generation(status: string, error_code: string | null = null) {
  return {
    id: `g-${status}`,
    status,
    error_code,
    asset_id: status === "succeeded" ? "made" : null,
    created_at: "2026-10-23T12:00:00Z",
    completed_at: null,
  };
}

export function routeApi(
  lists: ListShape[],
  started: unknown = generation("pending"),
): void {
  let call = 0;
  vi.mocked(apiCall).mockImplementation(
    (url: string, _schema, init?: RequestInit) => {
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
    },
  );
}

export function wrapper(client: QueryClient) {
  function Wrapper({ children }: { children: ReactNode }): React.ReactElement {
    return createElement(QueryClientProvider, { client }, children);
  }
  return Wrapper;
}

export function renderPanel(
  photos = PHOTOS,
  renderPromptSuggestions?: (fill: (prompt: string) => void) => ReactNode,
  uploadPhoto?: (file: File) => Promise<string>,
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const user = userEvent.setup();
  render(
    createElement(CoverGeneratePanel, {
      projectId: PROJECT,
      photos,
      renderPromptSuggestions,
      uploadPhoto,
    }),
    { wrapper: wrapper(client) },
  );
  return { user, client };
}

export async function fillForm(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByText(/^usage/);
  await user.click(screen.getByLabelText(/photoLabel \{"number":1\}/));
  await user.type(screen.getByRole("textbox"), PROMPT);
}

export function postBodies(): unknown[] {
  return vi
    .mocked(apiCall)
    .mock.calls.filter(([, , init]) => init?.method === HTTP_METHODS.POST)
    .map(
      ([, , init]) =>
        JSON.parse(
          typeof init?.body === "string" ? init.body : "null",
        ) as unknown,
    );
}
