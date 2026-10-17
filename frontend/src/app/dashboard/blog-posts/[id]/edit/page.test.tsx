import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { UseBlogPostEditorResult } from "@/modules/publishing";

// Scenarios: see tests/features/blog-dashboard-ae0411.feature (Editor)

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "p-1" }),
  useRouter: () => ({ push }),
}));

const editorState = vi.fn<() => UseBlogPostEditorResult>();
vi.mock("@/modules/publishing", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/publishing")>()),
  useBlogPostEditor: () => editorState(),
  VersionHistorySidebar: () => null,
  AiSuggestionPanel: () => null,
}));

import BlogPostEditPage from "@/app/dashboard/blog-posts/[id]/edit/page";

function state(
  overrides: Partial<UseBlogPostEditorResult>,
): UseBlogPostEditorResult {
  return {
    post: {
      id: "p-1",
      title: "Stored",
      slug: "s",
      status: "draft",
      content: {},
      editor_comments: [],
      version_history: [],
      sources: [],
      citations: [],
      ai_suggestions: [],
      ai_generation_metadata: {},
      keywords: [],
      view_count: 0,
      like_count: 0,
      comment_count: 0,
      share_count: 0,
      created_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-01T00:00:00Z",
      lock_version: 1,
    },
    loading: false,
    loadFailed: false,
    saving: false,
    title: "Stored",
    setTitle: vi.fn(),
    excerpt: "",
    setExcerpt: vi.fn(),
    bodyText: "# Body",
    setBodyText: vi.fn(),
    selectedText: "",
    setSelectedText: vi.fn(),
    validation: { title: null, excerpt: null },
    saveError: null,
    handleSave: vi.fn().mockResolvedValue(true),
    handleRestore: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  push.mockReset();
  editorState.mockReset();
});

describe("BlogPostEditPage (AE-0411)", () => {
  it("labels the fields with required and maxLength and shows the body", () => {
    editorState.mockReturnValue(state({}));
    render(<BlogPostEditPage />);
    const title = screen.getByLabelText("Title");
    expect(title).toBeRequired();
    expect(title).toHaveAttribute("maxLength", "255");
    expect(screen.getByLabelText("Excerpt")).toHaveAttribute(
      "maxLength",
      "500",
    );
    expect(screen.getByLabelText("Content")).toHaveValue("# Body");
  });

  it("returns to the list after a successful save", async () => {
    editorState.mockReturnValue(state({}));
    render(<BlogPostEditPage />);
    fireEvent.click(screen.getByText("Save changes"));
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/dashboard/blog-posts"),
    );
  });

  // Scenario: A server rejection is shown and the user stays on the editor
  it("stays on the editor and shows the error when the save fails", async () => {
    const handleSave = vi.fn().mockResolvedValue(false);
    editorState.mockReturnValue(
      state({ handleSave, saveError: "validation_failed" }),
    );
    render(<BlogPostEditPage />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The server rejected the changes",
    );
    fireEvent.click(screen.getByText("Save changes"));
    await waitFor(() => expect(handleSave).toHaveBeenCalled());
    expect(push).not.toHaveBeenCalled();
  });

  // Scenario: An empty title cannot be saved
  it("shows the title error and disables save when invalid", () => {
    editorState.mockReturnValue(
      state({
        title: "",
        validation: { title: "titleRequired", excerpt: null },
      }),
    );
    render(<BlogPostEditPage />);
    expect(screen.getByText("The title is required.")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByText("Save changes").closest("button")).toBeDisabled();
  });

  it("shows the excerpt limit error", () => {
    editorState.mockReturnValue(
      state({ validation: { title: null, excerpt: "excerptTooLong" } }),
    );
    render(<BlogPostEditPage />);
    expect(
      screen.getByText("The excerpt can have at most 500 characters."),
    ).toBeInTheDocument();
  });

  it("forwards body edits and selections", () => {
    const setBodyText = vi.fn();
    const setSelectedText = vi.fn();
    editorState.mockReturnValue(state({ setBodyText, setSelectedText }));
    render(<BlogPostEditPage />);
    const body = screen.getByLabelText("Content") as HTMLTextAreaElement;
    fireEvent.change(body, { target: { value: "# New" } });
    expect(setBodyText).toHaveBeenCalledWith("# New");
    body.setSelectionRange(2, 5);
    fireEvent.select(body);
    expect(setSelectedText).toHaveBeenCalledWith("Bod");
  });

  it("shows a load error when the post could not be loaded", () => {
    editorState.mockReturnValue(state({ post: undefined, loadFailed: true }));
    render(<BlogPostEditPage />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not load this post",
    );
  });

  it("shows not-found for a missing post", () => {
    editorState.mockReturnValue(state({ post: undefined }));
    render(<BlogPostEditPage />);
    expect(screen.getByText("Blog post not found.")).toBeInTheDocument();
  });
});
