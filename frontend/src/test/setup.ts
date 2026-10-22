import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi, beforeAll, afterAll } from "vitest";
import type { ReactNode } from "react";
import { server } from "./mocks/server";

vi.mock("next-intl", async () => {
  const messages = (await import("../i18n/locales/en.json")).default;

  const lookup = (path: string): unknown =>
    path.split(".").reduce<unknown>((current, segment) => {
      if (current && typeof current === "object" && segment in current) {
        return (current as Record<string, unknown>)[segment];
      }
      return undefined;
    }, messages);

  const format = (
    value: unknown,
    key: string,
    values?: Record<string, unknown>,
  ): string => {
    if (typeof value !== "string") return key;
    return value.replace(/\{(\w+)\}/g, (match, token: string) =>
      values && token in values ? String(values[token]) : match,
    );
  };

  type Translator = (key: string, values?: Record<string, unknown>) => string;
  const translators = new Map<string, Translator>();
  const translatorFor = (namespace?: string): Translator => {
    const cacheKey = namespace ?? "";
    const cached = translators.get(cacheKey);
    if (cached) return cached;
    const translate: Translator = (key, values) => {
      const fullKey = namespace ? `${namespace}.${key}` : key;
      return format(lookup(fullKey), key, values);
    };
    translators.set(cacheKey, translate);
    return translate;
  };

  return {
    NextIntlClientProvider: ({ children }: { children: ReactNode }) => children,
    useLocale: () => "en",
    useMessages: () => messages,
    useTranslations: translatorFor,
  };
});

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

afterEach(() => {
  cleanup();
});

if (!("matchMedia" in globalThis)) {
  global.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, "IntersectionObserver", {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

class MockResizeObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, "ResizeObserver", {
  writable: true,
  configurable: true,
  value: MockResizeObserver,
});

Object.defineProperty(window, "scrollTo", {
  writable: true,
  value: vi.fn(),
});
