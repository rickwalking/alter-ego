/**
 * The cover-photo prompt field: curated suggestions first, tapping one fills the
 * editable field, "More ideas" sends only the topic, palette and locale, and a
 * failure keeps the curated suggestions.
 */
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@/test/utils";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";
import { CoverPromptField } from "./cover-prompt-field";

const authenticatedFetch =
  vi.fn<(url: string, init?: RequestInit) => Promise<Response>>();

const PALETTE: CoverIdeasPalette = {
  name: "Night Blue",
  mode: "dark",
  background: "#0b1020",
  primary: "#38bdf8",
  accent: "#fde68a",
};
const AI_IDEAS = [
  "Seated on a stool, three-quarter view, deep navy backdrop",
  "Walking towards the camera in a corridor lit in sky blue",
  "Leaning on a wall, arms crossed, warm yellow rim light",
];

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  return input instanceof URL ? input.href : input.url;
}

/** A response the test settles by hand. */
function deferred(): {
  promise: Promise<Response>;
  resolve: (value: Response) => void;
} {
  const settlers: ((value: Response) => void)[] = [];
  const promise = new Promise<Response>((resolve) => {
    settlers.push(resolve);
  });
  return { promise, resolve: (value) => settlers[0]?.(value) };
}

function Harness({
  topic,
  palette,
}: Readonly<{ topic: string; palette: CoverIdeasPalette | null }>) {
  const [value, setValue] = useState("");
  return (
    <CoverPromptField
      id="cover-prompt"
      topic={topic}
      palette={palette}
      value={value}
      onChange={setValue}
    />
  );
}

function renderField(topic = "AI at work", palette = PALETTE) {
  render(<Harness topic={topic} palette={palette} />);
  return userEvent.setup();
}

function suggestions(name: string): HTMLElement[] {
  const section = screen.getByRole("region", { name });
  return within(section).getAllByRole("button", { name: /^Use the idea/ });
}

describe("CoverPromptField", () => {
  beforeEach(() => {
    authenticatedFetch.mockReset();
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) =>
      authenticatedFetch(requestUrl(input), init),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** Scenario: The Slide 1 photo shows curated suggestions for the topic and palette */
  it("shows six curated suggestions with the palette and the topic", () => {
    renderField();

    const ideas = suggestions("Suggestions");
    expect(ideas).toHaveLength(6);
    expect(ideas[0]).toHaveTextContent("in blue and yellow tones");
    expect(ideas[0]).not.toHaveTextContent("#0b1020");
    expect(ideas[0]).not.toHaveTextContent("AI at work");
    expect(authenticatedFetch).not.toHaveBeenCalled();
  });

  /** Scenario: Outras ideias shuffles the catalogue without an AI call */
  it("shows a new curated set on Other ideas", async () => {
    const user = renderField();
    const before = suggestions("Suggestions").map((idea) => idea.textContent);

    await user.click(screen.getByRole("button", { name: "Other ideas" }));

    const after = suggestions("Suggestions").map((idea) => idea.textContent);
    expect(after).toHaveLength(6);
    expect(after).not.toEqual(before);
    expect(authenticatedFetch).not.toHaveBeenCalled();
  });

  /** Scenario: Tapping a suggestion fills the prompt field, which stays editable */
  it("fills the editable prompt with the tapped suggestion", async () => {
    const user = renderField();
    const field = screen.getByLabelText("Prompt for the new photo");

    const picked = suggestions("Suggestions")[2]!;
    await user.click(picked);
    expect(field).toHaveValue(picked.textContent);

    await user.type(field, ", golden hour");
    expect((field as HTMLTextAreaElement).value.endsWith(", golden hour")).toBe(
      true,
    );
    expect(field).toHaveAttribute("maxLength", "400");
  });

  /** Scenario: More ideas asks the AI with only the topic and the palette */
  it("asks the AI with the topic, palette and locale and shows its ideas", async () => {
    authenticatedFetch.mockResolvedValueOnce(json({ ideas: AI_IDEAS }));
    const user = renderField("  AI at work  ");

    await user.click(screen.getByRole("button", { name: "More ideas" }));

    const section = await screen.findByRole("region", {
      name: "AI ideas for your topic",
    });
    expect(
      within(section)
        .getAllByRole("button", { name: /^Use the idea/ })
        .map((button) => button.textContent),
    ).toEqual(AI_IDEAS);
    expect(
      screen.queryByRole("region", { name: "Suggestions" }),
    ).not.toBeInTheDocument();
    const [url, init] = authenticatedFetch.mock.calls[0]!;
    expect(url).toContain("/api/carousels/cover-prompt-ideas");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({
      topic: "AI at work",
      palette: PALETTE,
      locale: "en",
    });

    await user.click(within(section).getAllByRole("button")[1]!);
    expect(screen.getByLabelText("Prompt for the new photo")).toHaveValue(
      AI_IDEAS[1],
    );
  });

  /** Scenario: More ideas asks the AI with only the topic and the palette */
  it("sends a null palette for the auto theme", async () => {
    authenticatedFetch.mockResolvedValueOnce(json({ ideas: AI_IDEAS }));
    render(<Harness topic="AI at work" palette={null} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "More ideas" }));

    await screen.findByRole("region", { name: "AI ideas for your topic" });
    const init = authenticatedFetch.mock.calls[0]![1];
    expect(JSON.parse(init?.body as string)).toEqual({
      topic: "AI at work",
      palette: null,
      locale: "en",
    });
  });

  /** Scenario: More ideas needs a topic */
  it("disables More ideas until the topic has three characters", () => {
    renderField(" ab ");

    expect(screen.getByRole("button", { name: "More ideas" })).toBeDisabled();
    expect(
      screen.getByText("Write the carousel topic to ask for more ideas."),
    ).toBeInTheDocument();
  });

  /** Scenario: More ideas needs a topic */
  it("enables More ideas at exactly three characters, without the hint", () => {
    renderField("abc");

    expect(screen.getByRole("button", { name: "More ideas" })).toBeEnabled();
    expect(
      screen.queryByText("Write the carousel topic to ask for more ideas."),
    ).not.toBeInTheDocument();
  });

  /** Scenario: A failed AI call keeps the curated suggestions */
  it("shows a retryable error and keeps the curated suggestions", async () => {
    authenticatedFetch.mockResolvedValue(
      json({ detail: "cover_prompt_ideas_unavailable" }, 503),
    );
    const user = renderField();

    await user.click(screen.getByRole("button", { name: "More ideas" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not generate ideas right now.",
    );
    expect(suggestions("Suggestions")).toHaveLength(6);
    expect(screen.getByRole("button", { name: "More ideas" })).toBeEnabled();
  });

  /** Scenario: AI ideas stay on screen while more load */
  it("keeps the previous AI ideas while more load", async () => {
    const later = deferred();
    authenticatedFetch
      .mockResolvedValueOnce(json({ ideas: AI_IDEAS }))
      .mockReturnValueOnce(later.promise);
    const user = renderField();
    const more = screen.getByRole("button", { name: "More ideas" });

    await user.click(more);
    await screen.findByRole("region", { name: "AI ideas for your topic" });
    await user.click(more);

    expect(more).toHaveAttribute("aria-busy", "true");
    expect(
      suggestions("AI ideas for your topic").map((b) => b.textContent),
    ).toEqual(AI_IDEAS);
    later.resolve(json({ ideas: [...AI_IDEAS].reverse() }));
    expect(
      (await screen.findByText(AI_IDEAS[2]!)).closest("li")?.previousSibling,
    ).toBeNull();
  });

  /** Scenario: AI ideas give way when the topic or palette changes */
  it("shows the catalogue again when the topic or palette changes", async () => {
    authenticatedFetch.mockResolvedValueOnce(json({ ideas: AI_IDEAS }));
    const { rerender } = render(
      <Harness topic="AI at work" palette={PALETTE} />,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "More ideas" }));
    await screen.findByRole("region", { name: "AI ideas for your topic" });
    rerender(<Harness topic="Remote work" palette={PALETTE} />);

    expect(suggestions("Suggestions")[0]).toHaveTextContent("headline");
    rerender(
      <Harness
        topic="AI at work"
        palette={{ ...PALETTE, accent: "#ffffff" }}
      />,
    );
    expect(suggestions("Suggestions")[2]).toHaveTextContent("white tones");
    rerender(<Harness topic="AI at work" palette={PALETTE} />);
    expect(suggestions("AI ideas for your topic")).toHaveLength(3);
  });

  /** Scenario: The prompt can be copied */
  it("copies the prompt and confirms it", async () => {
    const user = renderField();
    const copy = screen.getByRole("button", { name: "Copy" });
    expect(copy).toBeDisabled();

    await user.type(
      screen.getByLabelText("Prompt for the new photo"),
      "Side light",
    );
    await user.click(copy);

    expect(await navigator.clipboard.readText()).toBe("Side light");
    expect(screen.getByRole("button", { name: "Copied" })).toBeEnabled();
  });

  /** Scenario: The prompt can be copied */
  it("stays on Copy when the clipboard refuses", async () => {
    const user = renderField();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(
      new Error("denied"),
    );

    await user.type(screen.getByLabelText("Prompt for the new photo"), "x");
    await user.click(screen.getByRole("button", { name: "Copy" }));

    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });

  /** Scenario: A malformed AI answer or request is an error */
  it("treats fewer than three AI ideas as an error", async () => {
    authenticatedFetch.mockResolvedValueOnce(
      json({ ideas: AI_IDEAS.slice(0, 2) }),
    );
    const user = renderField();

    await user.click(screen.getByRole("button", { name: "More ideas" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(suggestions("Suggestions")).toHaveLength(6);
  });

  /** Scenario: A malformed AI answer or request is an error */
  it("does not send a topic longer than 500 characters", async () => {
    const user = renderField("t".repeat(501));

    await user.click(screen.getByRole("button", { name: "More ideas" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(authenticatedFetch).not.toHaveBeenCalled();
  });

  /** Scenario: AI ideas give way when the topic or palette changes */
  it("drops an error once the topic changes", async () => {
    authenticatedFetch.mockResolvedValueOnce(json({ detail: "x" }, 503));
    const { rerender } = render(
      <Harness topic="AI at work" palette={PALETTE} />,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "More ideas" }));
    await screen.findByRole("alert");
    rerender(<Harness topic="Remote work" palette={PALETTE} />);

    expect(screen.queryByRole("alert")).toBeNull();
  });
});
