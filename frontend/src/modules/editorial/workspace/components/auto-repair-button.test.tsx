// Gherkin: backend/tests/features/carousel_deterministic_repair.feature
// Scenarios: user repairs from the UI, run-in-progress banner path (not toast),
// completed carousel chains repair -> republish (via the onRepublishNeeded prop
// the publish page supplies).
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-client";
import { AutoRepairButton } from "./auto-repair-button";
import { useRepairCarousel } from "../hooks/use-repair-carousel";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, number>) =>
    values?.count === undefined ? key : `${key}:${String(values.count)}`,
}));

vi.mock("../hooks/use-repair-carousel", () => ({
  useRepairCarousel: vi.fn(),
}));

interface MutateOpts {
  onSuccess?: (data: unknown) => void;
  onError?: (error: unknown) => void;
}

const repairResponse = (overrides: Record<string, unknown> = {}) => ({
  project_id: "p1",
  status: "repaired",
  needs_republish: false,
  validation: {
    validation_status: "valid",
    validated_at: "2026-07-10T00:00:00Z",
    blocking: false,
    violations: [],
  },
  repaired: [
    {
      slide_index: 4,
      locale: "pt",
      repaired: true,
      repaired_codes: ["drafting_scaffold_present", "body_too_long"],
      remaining_codes: [],
    },
  ],
  ...overrides,
});

function mockRepair(
  behavior: (opts: MutateOpts) => void,
): ReturnType<typeof vi.fn> {
  const mutate = vi.fn((_vars: unknown, opts: MutateOpts) => behavior(opts));
  vi.mocked(useRepairCarousel).mockReturnValue({
    mutate,
    isPending: false,
    isError: false,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useRepairCarousel>);
  return mutate;
}

describe("AutoRepairButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("repairs, renders the per-slide summary, and refreshes state", async () => {
    const mutate = mockRepair((opts) => opts.onSuccess?.(repairResponse()));
    const onRepaired = vi.fn();
    render(<AutoRepairButton projectId="p1" onRepaired={onRepaired} />);

    await userEvent.click(screen.getByRole("button"));

    expect(mutate).toHaveBeenCalledWith(
      { projectId: "p1" },
      expect.objectContaining({ onSuccess: expect.any(Function) as unknown }),
    );
    expect(onRepaired).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("repair-summary")).toBeInTheDocument();
  });

  it("shows the in-progress banner path (not a toast) on a 409", async () => {
    const conflict = new ApiError(409, "busy", "resume_already_in_progress");
    mockRepair((opts) => opts.onError?.(conflict));
    const onRepaired = vi.fn();
    render(<AutoRepairButton projectId="p1" onRepaired={onRepaired} />);

    await userEvent.click(screen.getByRole("button"));

    expect(onRepaired).toHaveBeenCalledTimes(1);
    expect(screen.getByText("conflictInProgress")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("chains a republish for a completed carousel that needs it", async () => {
    mockRepair((opts) =>
      opts.onSuccess?.(repairResponse({ needs_republish: true })),
    );
    const onRepublishNeeded = vi.fn();
    const onRepaired = vi.fn();
    render(
      <AutoRepairButton
        projectId="p1"
        onRepaired={onRepaired}
        onRepublishNeeded={onRepublishNeeded}
      />,
    );

    await userEvent.click(screen.getByRole("button"));

    expect(onRepublishNeeded).toHaveBeenCalledTimes(1);
    expect(onRepaired).not.toHaveBeenCalled();
  });

  // AE-0414 — Gherkin: frontend/tests/features/content-review-manual-fixes-ae0414.feature
  // Scenario: Auto-fix that cannot fix anything says so
  it("says how many blockers it could not fix on a no-op", async () => {
    const blocker = {
      code: "heading_not_sentence_case_en",
      message: "m",
      slide_index: 1,
      locale: "en",
      field: "heading",
    };
    const warning = { ...blocker, severity: "warning" };
    mockRepair((opts) =>
      opts.onSuccess?.(
        repairResponse({
          status: "noop",
          validation: {
            validation_status: "invalid",
            validated_at: "2026-10-16T00:00:00Z",
            blocking: true,
            violations: [...Array.from({ length: 38 }, () => blocker), warning],
          },
          repaired: [
            {
              slide_index: 1,
              locale: "en",
              repaired: false,
              repaired_codes: [],
              remaining_codes: ["heading_not_sentence_case_en"],
            },
          ],
        }),
      ),
    );
    const onRepaired = vi.fn();
    render(<AutoRepairButton projectId="p1" onRepaired={onRepaired} />);

    await userEvent.click(screen.getByRole("button"));

    expect(screen.getByRole("alert")).toHaveTextContent("remaining:38");
    expect(screen.queryByText("noChanges")).not.toBeInTheDocument();
    expect(screen.queryByTestId("repair-summary")).not.toBeInTheDocument();
    // A no-op wrote nothing, so the state is not re-read.
    expect(onRepaired).not.toHaveBeenCalled();
  });

  it("falls back to the remaining codes when the report lists none", async () => {
    mockRepair((opts) =>
      opts.onSuccess?.(
        repairResponse({
          status: "noop",
          repaired: [
            {
              slide_index: 2,
              locale: "pt",
              repaired: false,
              repaired_codes: [],
              remaining_codes: ["body_too_long", "copy_too_many_lines"],
            },
          ],
        }),
      ),
    );
    render(<AutoRepairButton projectId="p1" />);

    await userEvent.click(screen.getByRole("button"));

    expect(screen.getByRole("alert")).toHaveTextContent("remaining:2");
  });

  // Scenario: Auto-fix with nothing left says there was nothing to fix
  it("says there was nothing to fix when the no-op leaves no blockers", async () => {
    mockRepair((opts) =>
      opts.onSuccess?.(repairResponse({ status: "noop", repaired: [] })),
    );
    render(<AutoRepairButton projectId="p1" />);

    await userEvent.click(screen.getByRole("button"));

    expect(screen.getByText("noChanges")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("lists the fixes and the blockers left after a partial repair", async () => {
    mockRepair((opts) =>
      opts.onSuccess?.(
        repairResponse({
          validation: {
            validation_status: "invalid",
            validated_at: "2026-10-16T00:00:00Z",
            blocking: true,
            violations: [
              { code: "body_too_long", message: "m", slide_index: 4 },
            ],
          },
        }),
      ),
    );
    const onRepaired = vi.fn();
    render(<AutoRepairButton projectId="p1" onRepaired={onRepaired} />);

    await userEvent.click(screen.getByRole("button"));

    expect(screen.getByTestId("repair-summary")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("remaining:1");
    expect(onRepaired).toHaveBeenCalledTimes(1);
  });
});
