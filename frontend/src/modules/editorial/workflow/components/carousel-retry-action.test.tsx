import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import { RETRY_KIND } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import type { CarouselRetryCapability } from "@/schemas/carousel-retry";
import { CarouselRetryAction } from "./carousel-retry-action";
import type { CarouselRetryActionProps } from "./types";

const labels = en.workflow.retry;

function capability(
  overrides: Partial<CarouselRetryCapability> = {},
): CarouselRetryCapability {
  return {
    can_retry: true,
    retry_kind: RETRY_KIND.REVISE,
    refusal_code: null,
    lock_version: 3,
    ...overrides,
  };
}

function renderAction(overrides: Partial<CarouselRetryActionProps> = {}): void {
  render(
    <NextIntlClientProvider locale="en" messages={en}>
      <CarouselRetryAction
        capability={capability()}
        pending={false}
        canSubmit
        error={null}
        onRetry={vi.fn()}
        {...overrides}
      />
    </NextIntlClientProvider>,
  );
}

describe("CarouselRetryAction", () => {
  // Scenario: A 202 shows the accepted toast
  it("calls onRetry from an enabled button", async () => {
    const onRetry = vi.fn();
    renderAction({ onRetry });
    await userEvent.click(screen.getByRole("button", { name: labels.action }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  // Scenario: The Retry button says what it will run
  it.each([
    [RETRY_KIND.REDRIVE, labels.kind.redrive],
    [RETRY_KIND.REVISE, labels.kind.revise],
    [RETRY_KIND.REOPEN, labels.kind.reopen],
  ])("explains a %s", (kind, text) => {
    renderAction({ capability: capability({ retry_kind: kind }) });
    expect(
      screen.getByRole("button", { name: labels.action }),
    ).toHaveAccessibleDescription(text);
  });

  // Scenario: The Retry button says what it will run
  it("says nothing for a kind it does not know", () => {
    renderAction({ capability: capability({ retry_kind: "new_kind" }) });
    expect(
      screen.getByRole("button", { name: labels.action }),
    ).not.toHaveAccessibleDescription();
  });

  // Scenario: The pending button stays while the request runs
  it("shows the pending label on a disabled button", () => {
    renderAction({ pending: true, canSubmit: false });
    const button = screen.getByRole("button");
    expect(button).toHaveTextContent(labels.pending);
    expect(button).toBeDisabled();
    expect(button).not.toHaveAccessibleDescription();
  });

  // Scenario: A 409 refusal shows its own text
  it("keeps the refusal next to the button", () => {
    renderAction({
      capability: null,
      canSubmit: false,
      error: labels.refusals.not_retryable,
    });
    expect(
      screen.getByRole("button", { name: labels.action }),
    ).toHaveAccessibleDescription(labels.refusals.not_retryable);
  });

  // Scenario: Retry stays disabled without a usable version
  it("says why a retryable carousel cannot be submitted", () => {
    renderAction({ canSubmit: false });
    const button = screen.getByRole("button", { name: labels.action });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription(labels.errors.unavailable);
  });

  // Scenario: A 409 refusal shows its own text
  it("prefers the refusal over the kind", () => {
    renderAction({ error: labels.errors.actionFailed });
    expect(
      screen.getByRole("button", { name: labels.action }),
    ).toHaveAccessibleDescription(labels.errors.actionFailed);
  });
});
