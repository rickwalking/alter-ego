import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CreateRunProgressBanner } from "./create-run-progress-banner";
import {
  EDITORIAL_RUN_CHECK_AGAIN_AFTER_MS,
  EDITORIAL_RUN_STAGES,
} from "@/constants/editorial-workflow";

// Scenarios: backend/tests/features/carousel_run_progress_reaper.feature
//   - User sees a live in-progress banner during a revision
//   - The banner is never permanent ("Check again" past the threshold)

vi.mock("next-intl", () => ({
  // Echo key + params so assertions can target the looked-up copy.
  useTranslations:
    () =>
    (key: string, params?: Record<string, unknown>): string =>
      params ? `${key}:${JSON.stringify(params)}` : key,
}));

function isoMinutesAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString();
}

afterEach(() => {
  vi.useRealTimers();
});

describe("CreateRunProgressBanner", () => {
  it("shows phase, stage, start time, and elapsed time", () => {
    render(
      <CreateRunProgressBanner
        currentPhase="content"
        runStartedAt={isoMinutesAgo(2)}
        runStage={EDITORIAL_RUN_STAGES.VALIDATING}
        onCheckAgain={() => undefined}
      />,
    );
    const banner = screen.getByTestId("run-progress-banner");
    expect(banner).toHaveTextContent('phase:{"phase":"content"}');
    expect(banner).toHaveTextContent("stage.validating");
    expect(banner).toHaveTextContent("startedAt:");
    expect(banner).toHaveTextContent('elapsed:{"minutes":2');
    expect(banner).toHaveTextContent("actionsDisabled");
    expect(banner).toHaveAttribute("role", "status");
  });

  it("hides Check again for a fresh run", () => {
    render(
      <CreateRunProgressBanner
        currentPhase="content"
        runStartedAt={isoMinutesAgo(1)}
        runStage={null}
        onCheckAgain={() => undefined}
      />,
    );
    expect(screen.queryByText("checkAgain")).toBeNull();
  });

  it("offers Check again past the stale threshold and fires the refetch", () => {
    const onCheckAgain = vi.fn();
    render(
      <CreateRunProgressBanner
        currentPhase="content"
        runStartedAt={new Date(
          Date.now() - EDITORIAL_RUN_CHECK_AGAIN_AFTER_MS - 1_000,
        ).toISOString()}
        runStage={EDITORIAL_RUN_STAGES.GENERATING}
        onCheckAgain={onCheckAgain}
      />,
    );
    expect(screen.getByText("stillRunningHint")).toBeInTheDocument();
    fireEvent.click(screen.getByText("checkAgain"));
    expect(onCheckAgain).toHaveBeenCalledTimes(1);
  });

  it("renders without elapsed details when run_started_at is missing", () => {
    // Pre-migration runs have no run_started_at — the banner still informs.
    render(
      <CreateRunProgressBanner
        currentPhase="design"
        runStartedAt={null}
        runStage={null}
        onCheckAgain={() => undefined}
      />,
    );
    const banner = screen.getByTestId("run-progress-banner");
    expect(banner).toHaveTextContent('phase:{"phase":"design"}');
    expect(banner).not.toHaveTextContent("startedAt:");
    expect(screen.queryByText("checkAgain")).toBeNull();
  });

  it("ignores unknown stages instead of looking up a missing key", () => {
    render(
      <CreateRunProgressBanner
        currentPhase="content"
        runStartedAt={isoMinutesAgo(1)}
        runStage="brand_new_stage"
        onCheckAgain={() => undefined}
      />,
    );
    const banner = screen.getByTestId("run-progress-banner");
    expect(banner).not.toHaveTextContent("stage.brand_new_stage");
  });
});
