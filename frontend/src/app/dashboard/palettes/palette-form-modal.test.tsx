/**
 * The New palette modal's AI generator: candidates, "Use" pre-fill without
 * saving, retryable failure with manual creation intact, and its absence from
 * the edit modal.
 */
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@/test/utils";
import type { CustomPalette } from "@/schemas/palette";
import { PaletteFormModal } from "./palette-form-modal";

const authenticatedFetch =
  vi.fn<(url: string, init?: RequestInit) => Promise<Response>>();

const CONTRAST = { text: 12.1, primary: 7.4, accent: 4.83 };
const CANDIDATES = [
  {
    name: "Noite Azul",
    primary: "#38bdf8",
    accent: "#f472b6",
    background: "#0b1020",
    mode: "dark",
    keywords: ["night", "blue"],
    contrast: CONTRAST,
  },
  {
    name: "Areia",
    primary: "#1d4ed8",
    accent: "#9a3412",
    background: "#f8f5ee",
    mode: "light",
    keywords: ["sand"],
    contrast: { text: 16.2, primary: 6.1, accent: 6.9 },
  },
  {
    name: "Floresta",
    primary: "#86efac",
    accent: "#fde68a",
    background: "#052e16",
    mode: "dark",
    keywords: [],
    contrast: { text: 15.0, primary: 11.2, accent: 13.4 },
  },
];

const PALETTE: CustomPalette = {
  id: "p-1",
  name: "Aurora",
  slug: "aurora-1234abcd",
  primary: "#102030",
  accent: "#405060",
  background: "#708090",
  mode: "dark",
  keywords: [],
  archived: false,
  created_by: null,
  created_at: "2026-10-22T00:00:00Z",
  updated_at: "2026-10-22T00:00:00Z",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  return input instanceof URL ? input.href : input.url;
}

function sentBody(call: number): Record<string, unknown> {
  const init = authenticatedFetch.mock.calls[call]?.[1];
  return JSON.parse(init?.body as string) as Record<string, unknown>;
}

function renderCreate(onSave = vi.fn()) {
  render(
    <PaletteFormModal onClose={vi.fn()} onSave={onSave} isPending={false} />,
  );
  return { user: userEvent.setup(), onSave };
}

async function generate(user: ReturnType<typeof userEvent.setup>) {
  await user.type(
    screen.getByLabelText("Describe the palette"),
    "  tropical night  ",
  );
  await user.click(screen.getByRole("button", { name: "Generate" }));
}

describe("PaletteFormModal generator", () => {
  beforeEach(() => {
    authenticatedFetch.mockReset();
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) =>
      authenticatedFetch(requestUrl(input), init),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** Scenario: Generating shows three candidates to pick from */
  it("shows three candidates with their swatch, name and contrast", async () => {
    authenticatedFetch.mockResolvedValueOnce(json({ candidates: CANDIDATES }));
    const { user } = renderCreate();
    await generate(user);
    const list = await screen.findByRole("list", { name: "AI suggestions" });
    const cards = within(list).getAllByRole("listitem");
    expect(cards).toHaveLength(3);
    expect(within(cards[0]!).getByText("Noite Azul")).toBeInTheDocument();
    expect(within(cards[0]!).getByText("Contrast 4.8:1")).toBeInTheDocument();
    expect(within(cards[0]!).getByRole("img")).toBeInTheDocument();
    expect(authenticatedFetch.mock.calls[0]?.[0]).toContain(
      "/api/palettes/generate",
    );
    expect(authenticatedFetch.mock.calls[0]?.[1]?.method).toBe("POST");
    expect(sentBody(0)).toEqual({ description: "tropical night" });
    expect(
      screen.getByRole("button", { name: "Generate again" }),
    ).toBeInTheDocument();
  });

  /** Scenario: Using a candidate pre-fills the form without saving */
  it("pre-fills the form from a candidate and saves only on Create", async () => {
    authenticatedFetch.mockResolvedValueOnce(json({ candidates: CANDIDATES }));
    const { user, onSave } = renderCreate();
    await generate(user);
    await user.click(await screen.findByRole("button", { name: "Use Areia" }));
    expect(screen.getByLabelText("Name")).toHaveValue("Areia");
    expect(screen.getByLabelText("Mode")).toHaveValue("light");
    expect(
      screen.getByRole("button", { name: "Remove keyword sand" }),
    ).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
    expect(authenticatedFetch).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Create" }));
    expect(onSave).toHaveBeenCalledWith({
      name: "Areia",
      primary: "#1d4ed8",
      accent: "#9a3412",
      background: "#f8f5ee",
      mode: "light",
      keywords: ["sand"],
    });
  });

  /** Scenario: A generator failure shows a retryable error */
  it("shows a retryable error and keeps manual creation", async () => {
    authenticatedFetch
      .mockResolvedValueOnce(
        json({ detail: "palette_generation_unavailable" }, 503),
      )
      .mockResolvedValueOnce(json({ candidates: CANDIDATES }));
    const { user, onSave } = renderCreate();
    await generate(user);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not generate palettes right now.",
    );
    await user.type(screen.getByLabelText("Name"), "Manual");
    await user.click(screen.getByRole("button", { name: "Create" }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Manual", mode: "dark" }),
    );
    await user.click(screen.getByRole("button", { name: "Generate" }));
    expect(
      await screen.findByRole("list", { name: "AI suggestions" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  /** Scenario: The generator needs a description */
  it("keeps Generate disabled until the description has three characters", async () => {
    const { user } = renderCreate();
    const button = screen.getByRole("button", { name: "Generate" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Describe the palette"), "  ab ");
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Describe the palette"), "c");
    expect(button).toBeEnabled();
  });

  /** Scenario: The edit modal has no generator */
  it("has no generator in the edit modal", () => {
    render(
      <PaletteFormModal
        palette={PALETTE}
        onClose={vi.fn()}
        onSave={vi.fn()}
        isPending={false}
      />,
    );
    expect(screen.queryByLabelText("Describe the palette")).toBeNull();
    expect(screen.getByLabelText("Name")).toHaveValue("Aurora");
  });
});
