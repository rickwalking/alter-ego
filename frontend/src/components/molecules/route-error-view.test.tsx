/**
 * AE-0154: shared RouteErrorView (extracted from the dashboard error.tsx boundaries).
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RouteErrorView } from "./route-error-view";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

describe("RouteErrorView", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  const baseError = Object.assign(new Error("boom"), { digest: "d1" });

  it("renders the namespace error title/description and a retry button", () => {
    render(
      <RouteErrorView
        error={baseError}
        reset={() => {}}
        namespace="chat"
        logLabel="Chat error:"
      />,
    );
    expect(screen.getByText("errorTitle")).toBeInTheDocument();
    expect(screen.getByText("errorDescription")).toBeInTheDocument();
    expect(screen.getByText("tryAgain")).toBeInTheDocument();
  });

  it("logs the error with the route's log label", () => {
    const spy = vi.spyOn(console, "error");
    render(
      <RouteErrorView
        error={baseError}
        reset={() => {}}
        namespace="knowledge"
        logLabel="Knowledge base error:"
      />,
    );
    expect(spy).toHaveBeenCalledWith("Knowledge base error:", baseError);
  });

  it("hides the raw error message by default and shows it when enabled", () => {
    const { rerender } = render(
      <RouteErrorView
        error={baseError}
        reset={() => {}}
        namespace="knowledge"
        logLabel="x"
      />,
    );
    expect(screen.queryByText("boom")).not.toBeInTheDocument();

    rerender(
      <RouteErrorView
        error={baseError}
        reset={() => {}}
        namespace="chat"
        logLabel="x"
        showErrorMessage
      />,
    );
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("invokes reset when the retry button is clicked", async () => {
    const reset = vi.fn();
    render(
      <RouteErrorView
        error={baseError}
        reset={reset}
        namespace="chat"
        logLabel="x"
      />,
    );
    await userEvent.click(screen.getByText("tryAgain"));
    expect(reset).toHaveBeenCalledOnce();
  });
});
