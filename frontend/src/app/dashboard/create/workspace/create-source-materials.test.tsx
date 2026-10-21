/**
 * Source materials panel, pinned while it was split into a data hook,
 * a form hook and presentational parts.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CreateSourceMaterials } from "./create-source-materials";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const authenticatedFetch = vi.fn<(...args: unknown[]) => Promise<Response>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (...args: unknown[]) => authenticatedFetch(...args),
}));

function source(id: string, title: string) {
  return {
    id,
    title,
    content: `${title} body`,
    source_type: "note",
    extracted_key_points: [],
  };
}

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

describe("CreateSourceMaterials (AE-0446)", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("loads the project's sources on mount", async () => {
    authenticatedFetch.mockResolvedValueOnce(
      ok({ items: [source("s1", "First")] }),
    );
    render(<CreateSourceMaterials projectId="p1" />);
    expect(await screen.findByText("First")).toBeInTheDocument();
  });

  it("adds a source on top of the list and resets the form", async () => {
    const onSourcesChange = vi.fn();
    authenticatedFetch
      .mockResolvedValueOnce(ok({ items: [source("s1", "First")] }))
      .mockResolvedValueOnce(ok(source("s2", "Second")));
    render(
      <CreateSourceMaterials
        projectId="p1"
        onSourcesChange={onSourcesChange}
      />,
    );
    await screen.findByText("First");

    fireEvent.change(screen.getByLabelText("fields.title"), {
      target: { value: " Second " },
    });
    fireEvent.change(screen.getByLabelText("fields.content"), {
      target: { value: "notes" },
    });
    fireEvent.submit(screen.getByLabelText("fields.title").closest("form")!);

    await waitFor(() =>
      expect(onSourcesChange).toHaveBeenLastCalledWith([
        source("s2", "Second"),
        source("s1", "First"),
      ]),
    );
    const [, init] = authenticatedFetch.mock.calls[1]!;
    expect(JSON.parse((init as { body: string }).body)).toEqual({
      title: "Second",
      content: "notes",
      source_type: "note",
    });
    expect(screen.getByLabelText("fields.title")).toHaveValue("");
  });

  it("shows the load error", async () => {
    authenticatedFetch.mockResolvedValueOnce(new Response("", { status: 500 }));
    render(<CreateSourceMaterials projectId="p1" />);
    expect(
      await screen.findByText("Failed to load sources"),
    ).toBeInTheDocument();
  });
});
