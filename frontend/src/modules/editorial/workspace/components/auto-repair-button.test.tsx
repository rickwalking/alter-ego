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
  useTranslations: () => (key: string) => key,
}));

vi.mock("../hooks/use-repair-carousel", () => ({
  useRepairCarousel: vi.fn(),
}));

type MutateOpts = {
  onSuccess?: (data: unknown) => void;
  onError?: (error: unknown) => void;
};

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
      expect.objectContaining({ onSuccess: expect.any(Function) }),
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
});
