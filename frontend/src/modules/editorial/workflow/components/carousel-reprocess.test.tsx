import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import type { CarouselReprocessCapability } from "@/schemas/carousel-reprocess";
import { CarouselReprocess } from "./carousel-reprocess";
import type { CarouselReprocessProps } from "./types";

function capability(
  overrides: Partial<CarouselReprocessCapability> = {},
): CarouselReprocessCapability {
  return {
    can_reprocess: true,
    refusal_code: null,
    stuck_kind: "dead_letter",
    run_id: "run-1",
    status: "dead_letter",
    last_phase: "content",
    last_error_code: "run_budget_exhausted",
    position: null,
    eta_seconds: null,
    lock_version: 4,
    ...overrides,
  };
}

function renderControl(overrides: Partial<CarouselReprocessProps> = {}) {
  const onReprocess = vi.fn();
  render(
    <NextIntlClientProvider locale="en" messages={en}>
      <CarouselReprocess
        capability={capability()}
        pending={false}
        canSubmit
        error={null}
        onReprocess={onReprocess}
        {...overrides}
      />
    </NextIntlClientProvider>,
  );
  return onReprocess;
}

describe("CarouselReprocess", () => {
  /** Scenario: Reprocess shows progress after acceptance */
  it("shows queued position and ETA without calling the run executing", () => {
    renderControl({
      capability: capability({
        status: "queued",
        position: 2,
        eta_seconds: 180,
        last_error_code: null,
      }),
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Queued for reprocessing · position 2 · estimated start in 3 min",
    );
    expect(screen.queryByText(/Reprocessing phase/)).not.toBeInTheDocument();
  });

  /** Scenario: Reprocess shows progress after acceptance */
  it("shows the running phase only when the accepted run is running", () => {
    renderControl({
      capability: capability({ status: "running", last_error_code: null }),
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Reprocessing phase Content",
    );
    expect(
      screen.queryByText(/Queued for reprocessing/),
    ).not.toBeInTheDocument();
  });

  /** Scenario: Reprocess shows progress after acceptance */
  it("shows only the safe failure code and never a raw last error", () => {
    const withRawError = {
      ...capability(),
      last_error: "sensitive raw exception",
    } as CarouselReprocessCapability;
    renderControl({ capability: withRawError });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Reprocessing failed (run_budget_exhausted).",
    );
    expect(
      screen.queryByText(/sensitive raw exception/),
    ).not.toBeInTheDocument();
  });

  /** Scenario: Not stuck reasons are accessible */
  it.each([
    "owner_waiting",
    "normal_queued",
    "fresh_running",
    "null_heartbeat",
    "unsupported",
  ] as const)("exposes the %s disabled reason", (refusalCode) => {
    renderControl({
      capability: capability({
        can_reprocess: false,
        refusal_code: refusalCode,
        status: "queued",
      }),
      canSubmit: false,
    });
    const button = screen.getByRole("button", {
      name: en.workflow.reprocess.action,
    });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription(
      en.workflow.reprocess.refusals[refusalCode],
    );
  });

  /** Scenario: Not stuck reasons are accessible */
  it("provides Portuguese action and accessible refusal translations", () => {
    expect(pt.workflow.reprocess.action).toBe("Reprocessar");
    expect(pt.workflow.reprocess.refusals.owner_waiting).not.toBe(
      en.workflow.reprocess.refusals.owner_waiting,
    );
    expect(pt.workflow.reprocess.refusals.fresh_running).toContain("parada");
  });
});
