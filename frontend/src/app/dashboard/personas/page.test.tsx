/**
 * The personas page: empty state, create/edit form, validation, server
 * errors, cancel guard, delete and search.
 */
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PersonasPage from "./page";

const authenticatedFetch =
  vi.fn<(url: string, init?: RequestInit) => Promise<Response>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (url: string, init?: RequestInit) =>
    authenticatedFetch(url, init),
}));

const PERSONA = {
  id: "p-1",
  name: "Pedro",
  description: "Tech lead voice",
  tone_attributes: { formal: 0.2, conversational: 0.9, humorous: 0.5 },
  writing_samples: ["I ship small PRs."],
  forbidden_phrases: ["game changer", "synergy"],
  preferred_phrases: ["in practice"],
  sentence_structure_preferences: "Short sentences",
  paragraph_style: null,
  opinion_expression: "Direct",
  expertise_areas: ["AI", "Python"],
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
  render(<PersonasPage />);
  await user.click(
    await screen.findByRole("button", { name: "Create your first persona" }),
  );
  return user;
}

async function openEditForm(): Promise<ReturnType<typeof userEvent.setup>> {
  const user = userEvent.setup();
  authenticatedFetch.mockResolvedValueOnce(list([PERSONA]));
  render(<PersonasPage />);
  await user.click(
    await screen.findByRole("button", { name: "Edit persona Pedro" }),
  );
  return user;
}

describe("PersonasPage", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("explains an empty list and opens the form from its button", async () => {
    // Scenario: An empty persona list offers to create the first persona
    await openNewForm();
    expect(
      screen.getByRole("heading", { name: "New persona" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Formal")).toHaveValue("0.3");
    expect(screen.getByLabelText("Conversational")).toHaveValue("0.8");
  });

  it("creates a persona with every voice field", async () => {
    // Scenario: A new persona is created with its voice fields
    const user = await openNewForm();
    await user.type(screen.getByLabelText("Name"), " Ana ");
    await user.type(screen.getByLabelText("Expertise areas"), "AI{Enter}");
    await user.type(screen.getByLabelText("Expertise areas"), "AI{Enter}");
    await user.type(screen.getByLabelText("Expertise areas"), "Data");
    await user.tab();
    fireEvent.change(screen.getByLabelText("Humorous"), {
      target: { value: "0.1" },
    });
    await user.type(
      screen.getByLabelText("Forbidden phrases"),
      "no entanto, porém{Enter}",
    );
    await user.click(screen.getByRole("button", { name: "Add sample" }));
    expect(screen.getByLabelText("Sample 1")).toHaveFocus();
    await user.type(screen.getByLabelText("Sample 1"), "A real post.");
    authenticatedFetch.mockResolvedValueOnce(
      json({ ...PERSONA, id: "p-2", name: "Ana" }, 201),
    );
    await user.click(screen.getByRole("button", { name: "Create persona" }));

    expect(await screen.findByText("Ana")).toBeInTheDocument();
    expect(authenticatedFetch.mock.calls[1]?.[1]?.method).toBe("POST");
    expect(sentBody(1)).toEqual({
      name: "Ana",
      description: null,
      tone_attributes: { formal: 0.3, conversational: 0.8, humorous: 0.1 },
      writing_samples: ["A real post."],
      forbidden_phrases: ["no entanto, porém"],
      preferred_phrases: [],
      sentence_structure_preferences: null,
      paragraph_style: null,
      opinion_expression: null,
      expertise_areas: ["AI", "Data"],
    });
  });

  it("loads a persona and saves the edit with PUT", async () => {
    // Scenario: An existing persona is edited and saved
    const user = await openEditForm();
    expect(screen.getByLabelText("Name")).toHaveValue("Pedro");
    expect(screen.getByLabelText("Sentence structure")).toHaveValue(
      "Short sentences",
    );
    expect(screen.getByLabelText("Sample 1")).toHaveValue("I ship small PRs.");
    expect(screen.getByLabelText("Formal")).toHaveValue("0.2");
    await user.click(screen.getByRole("button", { name: "Remove synergy" }));
    authenticatedFetch.mockResolvedValueOnce(json({ ...PERSONA, name: "P2" }));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("P2")).toBeInTheDocument();
    const [url, init] = authenticatedFetch.mock.calls[1] ?? [];
    expect(url).toBe("/api/personas/p-1");
    expect(init?.method).toBe("PUT");
    expect(sentBody(1)).toMatchObject({
      forbidden_phrases: ["game changer"],
      opinion_expression: "Direct",
      paragraph_style: null,
    });
  });

  it("blocks the save and marks each invalid field", async () => {
    // Scenario: Invalid fields block the save
    const user = await openNewForm();
    await user.click(screen.getByRole("button", { name: "Add sample" }));
    await user.type(screen.getByLabelText("Sample 1"), "   ");
    await user.click(screen.getByRole("button", { name: "Create persona" }));

    expect(screen.getByLabelText("Name")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByLabelText("Name")).toHaveFocus();
    expect(
      screen.getByText("Enter a name of 1 to 255 characters."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Sample 1")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(
      screen.getByText("Write the sample or remove it."),
    ).toBeInTheDocument();
    expect(authenticatedFetch).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Remove sample 1" }));
    expect(screen.queryByLabelText("Sample 1")).not.toBeInTheDocument();
  });

  it("shows the API's refusal in the form and keeps the values", async () => {
    // Scenario: A server refusal is shown in the persona form
    // Scenario: A failed create is shown on the personas and rubrics pages
    const user = await openNewForm();
    await user.type(screen.getByLabelText("Name"), "Dup");
    authenticatedFetch.mockResolvedValueOnce(
      json({ detail: "Persona name already used" }, 400),
    );
    await user.click(screen.getByRole("button", { name: "Create persona" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Persona name already used",
    );
    expect(screen.getByLabelText("Name")).toHaveValue("Dup");
  });

  it("asks before Cancel discards changes", async () => {
    // Scenario: Cancel asks before discarding persona changes
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false);
    const user = await openNewForm();
    await user.type(screen.getByLabelText("Name"), "Draft");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByLabelText("Name")).toHaveValue("Draft");

    confirm.mockReturnValueOnce(true);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(confirm).toHaveBeenCalledWith(
      "You have unsaved changes to this persona. Leave without saving?",
    );
    expect(
      screen.getByRole("button", { name: "Create your first persona" }),
    ).toBeInTheDocument();
    expect(authenticatedFetch).toHaveBeenCalledTimes(1);
  });

  it("deletes a persona after confirmation", async () => {
    // Scenario: Deleting a persona asks first
    const user = userEvent.setup();
    authenticatedFetch.mockResolvedValueOnce(list([PERSONA]));
    render(<PersonasPage />);
    await user.click(
      await screen.findByRole("button", { name: "Delete persona Pedro" }),
    );
    authenticatedFetch.mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    );
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Delete",
      }),
    );

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Create your first persona" }),
      ).toBeInTheDocument(),
    );
    expect(authenticatedFetch.mock.calls[1]?.[0]).toBe("/api/personas/p-1");
    expect(authenticatedFetch.mock.calls[1]?.[1]?.method).toBe("DELETE");
  });

  it("explains a persona still in use", async () => {
    // Scenario: Deleting a persona still in use explains why
    const user = userEvent.setup();
    authenticatedFetch.mockResolvedValueOnce(list([PERSONA]));
    render(<PersonasPage />);
    await user.click(
      await screen.findByRole("button", { name: "Delete persona Pedro" }),
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
      "This persona is still used by carousels or voice corrections, so it cannot be deleted.",
    );
    expect(screen.getByText("Pedro")).toBeInTheDocument();
  });

  it("says when a search has no match and opens the form from the tile", async () => {
    // Scenario: A search without matches says so
    const user = userEvent.setup();
    authenticatedFetch.mockResolvedValueOnce(list([PERSONA]));
    render(<PersonasPage />);
    await user.click(
      await screen.findByRole("button", { name: /Create Persona/ }),
    );
    expect(
      screen.getByRole("heading", { name: "New persona" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.type(screen.getByPlaceholderText("Search personas..."), "zzz");
    expect(
      screen.getByText('No results for "zzz". Try a different search term.'),
    ).toBeInTheDocument();
  });

  it("shows a translated message when the list cannot load", async () => {
    // Scenario: An empty persona list offers to create the first persona
    authenticatedFetch.mockResolvedValueOnce(json({}, 500));
    render(<PersonasPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load the personas.",
    );
  });
});
