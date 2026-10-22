/**
 * The rubrics page: empty state, create/edit form, validation, server errors,
 * cancel, unsaved-changes guard and delete.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RubricsPage from "./page";

const authenticatedFetch =
  vi.fn<(url: string, init?: RequestInit) => Promise<Response>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (url: string, init?: RequestInit) =>
    authenticatedFetch(url, init),
}));

const CRITERION = {
  id: "c-1",
  name: "Hook strength",
  description: "Does slide 1 stop the scroll?",
  weight: 0.4,
  evaluation_method: "ai_auto",
  min_threshold: 0.7,
  scoring_scale: "0-100",
  prompt_template: "Score {content}",
};

const RUBRIC = {
  id: "r-1",
  name: "Carousel quality",
  description: "Standard checks",
  criteria: [CRITERION],
  applicable_content_types: ["carousel"],
  is_default: false,
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
  version: 1,
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function list(items: unknown[]): Response {
  return json({ items, total: items.length });
}

function sentBody(call: number): Record<string, unknown> {
  const init = authenticatedFetch.mock.calls[call]?.[1];
  return JSON.parse(init?.body as string) as Record<string, unknown>;
}

async function openNewForm(): Promise<ReturnType<typeof userEvent.setup>> {
  const user = userEvent.setup();
  authenticatedFetch.mockResolvedValueOnce(list([]));
  render(<RubricsPage />);
  await user.click(
    await screen.findByRole("button", { name: "Create your first rubric" }),
  );
  return user;
}

describe("RubricsPage", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("explains an empty list and opens the form from its button", async () => {
    // Scenario: An empty rubric list offers to create the first rubric
    await openNewForm();
    expect(
      screen.getByRole("heading", { name: "New rubric" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("");
    expect(screen.getByRole("checkbox", { name: "Carousel" })).toBeChecked();
  });

  it("creates a rubric with its content types and criteria", async () => {
    // Scenario: A new rubric is created with its criteria
    const user = await openNewForm();
    await user.type(screen.getByLabelText("Name"), "  Blog checks ");
    await user.click(screen.getByRole("checkbox", { name: "Blog post" }));
    await user.click(screen.getByRole("button", { name: "Add criterion" }));
    expect(screen.getByLabelText("Criterion name")).toHaveFocus();
    await user.type(screen.getByLabelText("Criterion name"), "Clarity");
    await user.selectOptions(
      screen.getByLabelText("Scoring scale"),
      "pass_fail",
    );
    authenticatedFetch.mockResolvedValueOnce(
      json({ ...RUBRIC, id: "r-2", name: "Blog checks" }, 201),
    );
    await user.click(screen.getByRole("button", { name: "Create rubric" }));

    expect(await screen.findByText("Blog checks")).toBeInTheDocument();
    const [url, init] = authenticatedFetch.mock.calls[1] ?? [];
    expect(url).toBe("/api/rubrics");
    expect(init?.method).toBe("POST");
    const body = sentBody(1);
    expect(body).toMatchObject({
      name: "Blog checks",
      description: null,
      applicable_content_types: ["carousel", "blog_post"],
    });
    expect(body.criteria).toEqual([
      expect.objectContaining({
        name: "Clarity",
        weight: 0.5,
        min_threshold: 0.7,
        evaluation_method: "ai_auto",
        scoring_scale: "pass_fail",
      }),
    ]);
  });

  it("loads a rubric into the form and saves the edit with PUT", async () => {
    // Scenario: An existing rubric is edited and saved
    const user = userEvent.setup();
    authenticatedFetch.mockResolvedValueOnce(list([RUBRIC]));
    render(<RubricsPage />);
    await user.click(
      await screen.findByRole("button", {
        name: "Edit rubric Carousel quality",
      }),
    );

    expect(screen.getByLabelText("Name")).toHaveValue("Carousel quality");
    expect(screen.getByLabelText("Description")).toHaveValue("Standard checks");
    expect(screen.getByLabelText("Criterion name")).toHaveValue(
      "Hook strength",
    );
    const weight = screen.getByLabelText("Weight (0–1)");
    expect(weight).toHaveValue(0.4);
    await user.clear(weight);
    await user.type(weight, "0.9");
    authenticatedFetch.mockResolvedValueOnce(
      json({ ...RUBRIC, name: "Edited" }),
    );
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Edited")).toBeInTheDocument();
    const [url, init] = authenticatedFetch.mock.calls[1] ?? [];
    expect(url).toBe("/api/rubrics/r-1");
    expect(init?.method).toBe("PUT");
    expect(sentBody(1).criteria).toEqual([{ ...CRITERION, weight: 0.9 }]);
  });

  it("reorders and removes criteria", async () => {
    // Scenario: Criteria are added, reordered and removed
    const user = await openNewForm();
    await user.click(screen.getByRole("button", { name: "Add criterion" }));
    await user.type(screen.getByLabelText("Criterion name"), "First");
    await user.click(screen.getByRole("button", { name: "Add criterion" }));
    const names = (): string[] =>
      screen
        .getAllByLabelText("Criterion name")
        .map((input) => (input as HTMLInputElement).value);
    await user.type(screen.getAllByLabelText("Criterion name")[1]!, "Second");

    expect(
      screen.getByRole("button", { name: "Move criterion 1 up" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Move criterion 2 down" }),
    ).toBeDisabled();
    await user.click(
      screen.getByRole("button", { name: "Move criterion 2 up" }),
    );
    expect(names()).toEqual(["Second", "First"]);
    await user.click(
      screen.getByRole("button", { name: "Move criterion 1 down" }),
    );
    expect(names()).toEqual(["First", "Second"]);
    await user.click(
      screen.getByRole("button", { name: "Remove criterion 1" }),
    );
    expect(names()).toEqual(["Second"]);
  });

  it("blocks the save and marks each invalid field", async () => {
    // Scenario: Invalid fields block the save
    const user = await openNewForm();
    await user.click(screen.getByRole("checkbox", { name: "Carousel" }));
    await user.click(screen.getByRole("button", { name: "Add criterion" }));
    const weight = screen.getByLabelText("Weight (0–1)");
    await user.clear(weight);
    await user.type(weight, "2");
    await user.click(screen.getByRole("button", { name: "Create rubric" }));

    expect(screen.getByLabelText("Name")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByLabelText("Name")).toHaveFocus();
    expect(
      screen.getByText("Enter a name of 1 to 255 characters."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Choose at least one content type."),
    ).toBeInTheDocument();
    expect(screen.getByText("Enter the criterion's name.")).toBeInTheDocument();
    expect(weight).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Enter a number from 0 to 1.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Fix the highlighted fields before saving.",
    );
    expect(authenticatedFetch).toHaveBeenCalledTimes(1);
  });

  it("shows the API's refusal in the form and keeps the values", async () => {
    // Scenario: A server refusal is shown in the form
    const user = await openNewForm();
    await user.type(screen.getByLabelText("Name"), "Dup");
    authenticatedFetch.mockResolvedValueOnce(
      json({ detail: "Rubric name already used" }, 400),
    );
    await user.click(screen.getByRole("button", { name: "Create rubric" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Rubric name already used",
    );
    expect(screen.getByLabelText("Name")).toHaveValue("Dup");
  });

  it("falls back to the translated message for a validation error list", async () => {
    // Scenario: A server refusal is shown in the form
    const user = await openNewForm();
    await user.type(screen.getByLabelText("Name"), "Bad");
    authenticatedFetch.mockResolvedValueOnce(
      json({ detail: [{ loc: ["body"], msg: "bad" }] }, 422),
    );
    await user.click(screen.getByRole("button", { name: "Create rubric" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The rubric could not be saved. Check the fields and try again.",
    );
  });

  it("cancels without saving once leaving is confirmed", async () => {
    // Scenario: Cancel leaves the form without saving
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = await openNewForm();
    await user.type(screen.getByLabelText("Name"), "Draft");
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(confirm).toHaveBeenCalledWith(
      "You have unsaved changes to this rubric. Leave without saving?",
    );
    expect(
      screen.getByRole("button", { name: "Create your first rubric" }),
    ).toBeInTheDocument();
    expect(authenticatedFetch).toHaveBeenCalledTimes(1);
  });

  it("cancels an untouched form without asking", async () => {
    // Scenario: Cancel leaves the form without saving
    const confirm = vi.spyOn(window, "confirm");
    const user = await openNewForm();
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(confirm).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "New Rubric" }),
    ).toBeInTheDocument();
  });

  it("keeps the form open when leaving is declined", async () => {
    // Scenario: Unsaved changes ask before leaving
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = await openNewForm();
    await user.type(screen.getByLabelText("Name"), "Draft");
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByLabelText("Name")).toHaveValue("Draft");
  });

  it("deletes after confirmation and explains a rubric still in use", async () => {
    // Scenario: Deleting a rubric asks first and explains a rubric in use
    const user = userEvent.setup();
    const used = { ...RUBRIC, id: "r-2", name: "Used" };
    const other = { ...RUBRIC, id: "r-9", name: "Default", is_default: true };
    authenticatedFetch.mockResolvedValueOnce(list([RUBRIC, used, other]));
    render(<RubricsPage />);
    await user.click(
      await screen.findByRole("button", {
        name: "Delete rubric Carousel quality",
      }),
    );
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByRole("button", { name: "Cancel" }),
    ).toHaveFocus();
    authenticatedFetch.mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    );
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(screen.queryByText("Carousel quality")).not.toBeInTheDocument(),
    );
    expect(authenticatedFetch.mock.calls[1]?.[0]).toBe("/api/rubrics/r-1");
    expect(authenticatedFetch.mock.calls[1]?.[1]?.method).toBe("DELETE");

    await user.click(
      screen.getByRole("button", { name: "Delete rubric Used" }),
    );
    authenticatedFetch.mockResolvedValueOnce(
      json({ error: "conflict", message: "IntegrityError", details: {} }, 409),
    );
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Delete",
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This rubric is still used by carousels or evaluations, so it cannot be deleted.",
    );
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Cancel",
      }),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText("Used")).toBeInTheDocument();
  });

  it("offers no delete for the default rubric", async () => {
    // Scenario: The default rubric cannot be deleted from the list
    const other = { ...RUBRIC, id: "r-9", name: "Default", is_default: true };
    authenticatedFetch.mockResolvedValueOnce(list([other]));
    render(<RubricsPage />);
    expect(
      await screen.findByRole("button", { name: "Edit rubric Default" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Delete rubric Default" }),
    ).not.toBeInTheDocument();
  });

  it("shows the fallback when a delete fails without a message", async () => {
    // Scenario: Deleting a rubric asks first and explains a rubric in use
    const user = userEvent.setup();
    authenticatedFetch.mockResolvedValueOnce(list([RUBRIC]));
    render(<RubricsPage />);
    await user.click(
      await screen.findByRole("button", {
        name: "Delete rubric Carousel quality",
      }),
    );
    authenticatedFetch.mockResolvedValueOnce(json({}, 500));
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Delete",
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The rubric could not be deleted.",
    );
  });

  it("shows a translated message when the list cannot load", async () => {
    // Scenario: An empty rubric list offers to create the first rubric
    authenticatedFetch.mockResolvedValueOnce(json({}, 500));
    render(<RubricsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load the rubrics.",
    );
  });
});
