/**
 * The rubrics page: leaving the editor (Cancel and Escape, through the in-app
 * leave dialog when there are unsaved changes) and the keyboard path through
 * the rubric list.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RubricsPage from "./page";

const authenticatedFetch =
  vi.fn<(url: string, init?: RequestInit) => Promise<Response>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (url: string, init?: RequestInit) =>
    authenticatedFetch(url, init),
}));

const RUBRIC = {
  id: "r-1",
  name: "Carousel quality",
  description: "Standard checks",
  criteria: [
    {
      id: "c-1",
      name: "Hook strength",
      description: "Does slide 1 stop the scroll?",
      weight: 0.4,
      evaluation_method: "ai_auto",
      min_threshold: 0.7,
      scoring_scale: "0-100",
      prompt_template: "Score {content}",
    },
  ],
  applicable_content_types: ["carousel"],
  is_default: false,
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
  version: 1,
};

const DEFAULT_RUBRIC = { ...RUBRIC, id: "r-9", name: "Base", is_default: true };
const LEAVE_TITLE = "Discard your changes?";

type User = ReturnType<typeof userEvent.setup>;

function listResponse(items: unknown[]): Response {
  return new Response(JSON.stringify({ items, total: items.length }));
}

async function openEditor(): Promise<User> {
  const user = userEvent.setup();
  authenticatedFetch.mockResolvedValueOnce(listResponse([RUBRIC]));
  render(<RubricsPage />);
  await user.click(
    await screen.findByRole("button", { name: "Edit rubric Carousel quality" }),
  );
  return user;
}

async function openChangedEditor(): Promise<User> {
  const user = await openEditor();
  await user.clear(screen.getByLabelText("Name"));
  await user.type(screen.getByLabelText("Name"), "Draft");
  return user;
}

function expectListShown(): void {
  expect(
    screen.getByRole("button", { name: "Edit rubric Carousel quality" }),
  ).toBeInTheDocument();
  expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
}

describe("RubricsPage leaving the editor", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("asks in a modal dialog, then keeps editing with focus back on Cancel", async () => {
    // Scenario: Discarding unsaved changes asks in an in-app dialog
    const nativeConfirm = vi.spyOn(window, "confirm");
    const user = await openChangedEditor();
    const cancel = screen.getByRole("button", { name: "Cancel" });
    await user.click(cancel);

    const dialog = screen.getByRole("dialog", { name: LEAVE_TITLE });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveTextContent(
      "You have unsaved changes to this rubric. Leave without saving?",
    );
    expect(screen.getByRole("button", { name: "Keep editing" })).toHaveFocus();
    expect(nativeConfirm).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Keep editing" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("Draft");
    expect(cancel).toHaveFocus();
  });

  it("keeps focus inside the dialog while it is open", async () => {
    // Scenario: Discarding unsaved changes asks in an in-app dialog
    const user = await openChangedEditor();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    const stay = screen.getByRole("button", { name: "Keep editing" });
    const leave = screen.getByRole("button", { name: "Leave without saving" });

    await user.tab();
    expect(leave).toHaveFocus();
    await user.tab();
    expect(stay).toHaveFocus();
    await user.tab({ shift: true });
    expect(leave).toHaveFocus();
  });

  it("leaves without saving once the dialog is confirmed", async () => {
    // Scenario: Discarding unsaved changes asks in an in-app dialog
    const user = await openChangedEditor();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.click(
      screen.getByRole("button", { name: "Leave without saving" }),
    );

    await waitFor(expectListShown);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(authenticatedFetch).toHaveBeenCalledTimes(1);
  });

  it("cancels an untouched form without asking", async () => {
    // Scenario: Discarding unsaved changes asks in an in-app dialog
    const user = await openEditor();
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expectListShown();
  });

  it("closes an untouched editor on Escape", async () => {
    // Scenario: Escape cancels the editor
    const user = await openEditor();
    await user.keyboard("{Escape}");

    expectListShown();
    expect(authenticatedFetch).toHaveBeenCalledTimes(1);
  });

  it("sends Escape on a changed editor through the dialog", async () => {
    // Scenario: Escape on a changed editor goes through the dialog
    const user = await openChangedEditor();
    await user.keyboard("{Escape}");
    expect(
      screen.getByRole("dialog", { name: LEAVE_TITLE }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("Draft");

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("Draft");
    expect(screen.getByLabelText("Name")).toHaveFocus();
  });
});

describe("RubricsPage keyboard path", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("tabs through each rubric's Edit then Delete in list order", async () => {
    // Scenario: Each row's actions are reachable by Tab in order
    const user = userEvent.setup();
    const second = { ...RUBRIC, id: "r-2", name: "Blog checks" };
    authenticatedFetch.mockResolvedValueOnce(
      listResponse([RUBRIC, DEFAULT_RUBRIC, second]),
    );
    render(<RubricsPage />);
    await screen.findByText("Blog checks");

    const expected = [
      "New Rubric",
      "Edit rubric Carousel quality",
      "Delete rubric Carousel quality",
      "Edit rubric Base",
      "Edit rubric Blog checks",
      "Delete rubric Blog checks",
    ];
    for (const name of expected) {
      await user.tab();
      const button = screen.getByRole("button", { name });
      expect(button).toHaveFocus();
      expect(button).toHaveClass("focus-visible:ring-2");
    }
  });
});
