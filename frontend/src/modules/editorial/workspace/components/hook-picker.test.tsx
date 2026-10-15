import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import { HookPicker } from "./hook-picker";

// Gherkin: backend/tests/features/carousel_pov_prompts.feature (Hook pick, AE-0375)
const mutate = vi.fn();
const state = { isPending: false, isSuccess: false, isError: false };

vi.mock("@/modules/editorial/workspace/hooks/use-save-hook", () => ({
  useSaveCarouselHook: () => ({ mutate, ...state }),
}));

const CANDIDATES = ["Pare de pedir código pra IA", "Opinião impopular: decida"];

describe("HookPicker", () => {
  beforeEach(() => {
    mutate.mockReset();
    state.isPending = false;
    state.isSuccess = false;
    state.isError = false;
  });

  it("lists the candidates and marks the current hook", () => {
    render(
      <HookPicker
        projectId="p1"
        candidates={CANDIDATES}
        initialHook={CANDIDATES[0]}
      />,
    );
    expect(screen.getByRole("radio", { name: CANDIDATES[0] })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: CANDIDATES[1] })).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("saves the picked candidate", () => {
    render(
      <HookPicker
        projectId="p1"
        candidates={CANDIDATES}
        initialHook={CANDIDATES[0]}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: CANDIDATES[1] }));
    fireEvent.click(screen.getByRole("button", { name: "Save hook" }));
    expect(mutate).toHaveBeenCalledWith({
      projectId: "p1",
      hookText: CANDIDATES[1],
    });
  });

  it("saves an edited hook, trimmed", () => {
    render(
      <HookPicker projectId="p1" candidates={CANDIDATES} initialHook="" />,
    );
    fireEvent.change(screen.getByLabelText(/Hook \(max 60/), {
      target: { value: "  Meu gancho  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save hook" }));
    expect(mutate).toHaveBeenCalledWith({
      projectId: "p1",
      hookText: "Meu gancho",
    });
  });

  it("blocks a hook with more than 10 words or none", () => {
    render(
      <HookPicker
        projectId="p1"
        candidates={CANDIDATES}
        initialHook={Array(11).fill("palavra").join(" ")}
      />,
    );
    expect(screen.getByText("11 of 10 words")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save hook" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Hook \(max 60/), {
      target: { value: "   " },
    });
    expect(screen.getByRole("button", { name: "Save hook" })).toBeDisabled();
  });

  it("warns when the thesis is not on slides 1-2", () => {
    render(
      <HookPicker
        projectId="p1"
        candidates={CANDIDATES}
        initialHook=""
        thesisEarly={false}
      />,
    );
    expect(screen.getByRole("note")).toHaveTextContent(
      /thesis does not show up/,
    );
  });

  it("shows saved and failed states", () => {
    state.isSuccess = true;
    const { rerender } = render(
      <HookPicker projectId="p1" candidates={CANDIDATES} initialHook="x" />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/Hook saved/);
    state.isSuccess = false;
    state.isError = true;
    rerender(
      <HookPicker projectId="p1" candidates={CANDIDATES} initialHook="x" />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/Could not save/);
  });
});
