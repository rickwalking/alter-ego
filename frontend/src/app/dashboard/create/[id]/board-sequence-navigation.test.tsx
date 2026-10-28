import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY } from "@/modules/editorial-operations/board/workflow/constants";
import { BoardSequenceNavigation } from "./board-sequence-navigation";

const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));
vi.mock("next-intl", () => ({
  useTranslations:
    () =>
    (
      key: string,
      values?: { position: number; total: number; column: string },
    ) =>
      key === "position" && values !== undefined
        ? `${values.position} / ${values.total} in ${values.column}`
        : key,
}));

function storeSequence(): void {
  window.sessionStorage.setItem(
    WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY,
    JSON.stringify({ column: "Final review", ids: ["p1", "p2", "p3"] }),
  );
}

describe("BoardSequenceNavigation", () => {
  /** Scenario: Previous and next controls follow the board column sequence */
  it("hides the controls without a matching stored sequence", () => {
    const { container } = render(<BoardSequenceNavigation projectId="p2" />);
    expect(container).toBeEmptyDOMElement();
  });

  /** Scenario: Previous and next controls follow the board column sequence */
  it("shows the position and navigates to adjacent cards", async () => {
    storeSequence();
    const user = userEvent.setup();
    render(<BoardSequenceNavigation projectId="p2" />);
    expect(
      await screen.findByText("2 / 3 in Final review"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "previous" }));
    expect(router.push).toHaveBeenCalledWith("/dashboard/create/p1");
    await user.click(screen.getByRole("button", { name: "next" }));
    expect(router.push).toHaveBeenCalledWith("/dashboard/create/p3");
  });

  /** Scenario: Previous and next controls follow the board column sequence */
  it("supports bracket shortcuts outside editable fields", async () => {
    storeSequence();
    render(<BoardSequenceNavigation projectId="p2" />);
    await screen.findByText("2 / 3 in Final review");
    fireEvent.keyDown(window, { key: "[" });
    expect(router.push).toHaveBeenCalledWith("/dashboard/create/p1");
    fireEvent.keyDown(window, { key: "]" });
    expect(router.push).toHaveBeenCalledWith("/dashboard/create/p3");
  });

  /** Scenario: Previous and next controls follow the board column sequence */
  it("ignores bracket shortcuts with modifier keys", async () => {
    storeSequence();
    render(<BoardSequenceNavigation projectId="p2" />);
    await screen.findByText("2 / 3 in Final review");
    fireEvent.keyDown(window, { key: "[", metaKey: true });
    fireEvent.keyDown(window, { key: "]", ctrlKey: true });
    fireEvent.keyDown(window, { key: "[", altKey: true });
    expect(router.push).not.toHaveBeenCalled();
  });

  /** Scenario: Previous and next controls follow the board column sequence */
  it("groups its controls with an accessible label", async () => {
    storeSequence();
    render(<BoardSequenceNavigation projectId="p2" />);
    expect(
      await screen.findByRole("group", { name: "label" }),
    ).toBeInTheDocument();
  });

  /** Scenario: Previous and next controls follow the board column sequence */
  it("ignores bracket shortcuts while editing text", async () => {
    storeSequence();
    render(
      <>
        <input aria-label="Topic" />
        <BoardSequenceNavigation projectId="p2" />
      </>,
    );
    await screen.findByText("2 / 3 in Final review");
    const input = screen.getByRole("textbox", { name: "Topic" });
    input.focus();
    fireEvent.keyDown(input, { key: "]" });
    expect(router.push).not.toHaveBeenCalled();
  });

  beforeEach(() => {
    window.sessionStorage.clear();
    router.push.mockClear();
  });
});
