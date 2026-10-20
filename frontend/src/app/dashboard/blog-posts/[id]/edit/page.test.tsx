import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { UseBlogPostEditorResult } from "@/modules/publishing";
import {
  blogPost,
  SEC_1,
  v2Document,
} from "@/modules/publishing/blog/editor.test-utils";

// Scenarios: tests/features/blog_editor_ae0424.feature (editor wiring,
// unsaved guard, conflict, migration banner, localized copy) and
// tests/features/blog-dashboard-ae0411.feature (Editor)

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "p-1" }),
  useRouter: () => ({ push }),
}));

const editorState = vi.fn<() => UseBlogPostEditorResult>();
const confirmLeave = vi.fn(() => true);
const slotsPending = vi.fn(() => false);
let capturedApply: ((text: string) => void) | null = null;
let capturedUnsaved: boolean | null = null;
vi.mock("@/modules/publishing", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/publishing")>()),
  useBlogPostEditor: () => editorState(),
  useBlogEditorData: () => ({
    versions: [],
    versionsLoading: false,
    personas: [],
    personaId: null,
    setPersonaId: vi.fn(),
  }),
  useBlogEditorActions: () => ({
    statusOf: () => ({ pending: false, error: null }),
    anyPending: slotsPending(),
    generateImage: vi.fn(),
    rewrite: vi.fn(),
    generateTranslation: vi.fn(),
  }),
  useBlogReviewActions: () => ({
    allowSelfReview: false,
    pending: false,
    error: null,
  }),
  useUnsavedChangesGuard: () => ({ confirmLeave }),
  // AE-0425: the generation banner has its own tests (blog-generation-status).
  BlogGenerationStatus: (props: { unsavedChanges?: boolean }) => {
    capturedUnsaved = props.unsavedChanges ?? null;
    return null;
  },
  AiSuggestionPanel: ({
    onApplySuggestion,
  }: {
    onApplySuggestion: (text: string) => void;
  }) => {
    capturedApply = onApplySuggestion;
    return null;
  },
}));

import BlogPostEditPage from "@/app/dashboard/blog-posts/[id]/edit/page";

function state(
  overrides: Partial<UseBlogPostEditorResult> = {},
): UseBlogPostEditorResult {
  return {
    post: blogPost(),
    loading: false,
    loadFailed: false,
    draft: { title: "GPT 5.6 saiu", excerpt: "", document: v2Document() },
    language: "pt",
    setLanguage: vi.fn(),
    updateDraft: vi.fn(),
    validation: { title: null, excerpt: null, document: {} },
    dirty: false,
    saving: false,
    error: null,
    setError: vi.fn(),
    handleSave: vi.fn().mockResolvedValue(true),
    ensureSaved: vi.fn(),
    applyServerPost: vi.fn(),
    replaceFromServer: vi.fn(),
    reload: vi.fn(),
    handleRestore: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  push.mockReset();
  editorState.mockReset();
  confirmLeave.mockReset();
  confirmLeave.mockReturnValue(true);
  capturedApply = null;
});

describe("BlogPostEditPage (AE-0424)", () => {
  // Scenario: The editor shows one card per section (AC1)
  it("shows the title/excerpt fields and one card per section", () => {
    editorState.mockReturnValue(state());
    render(<BlogPostEditPage />);
    const title = screen.getByLabelText("Title");
    expect(title).toBeRequired();
    expect(title).toHaveAttribute("maxLength", "255");
    expect(screen.getByLabelText("Excerpt")).toHaveAttribute(
      "maxLength",
      "500",
    );
    expect(screen.getAllByText(/^Section \d$/)).toHaveLength(3);
    expect(screen.queryByLabelText("Content")).not.toBeInTheDocument();
  });

  it("saves only when dirty and stays on the editor", () => {
    const handleSave = vi.fn().mockResolvedValue(true);
    editorState.mockReturnValue(state({ handleSave }));
    const { rerender } = render(<BlogPostEditPage />);
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
    editorState.mockReturnValue(state({ handleSave, dirty: true }));
    rerender(<BlogPostEditPage />);
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(handleSave).toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  // Scenario: Leaving with unsaved changes is guarded
  it("asks before going back with unsaved changes", () => {
    editorState.mockReturnValue(state({ dirty: true }));
    render(<BlogPostEditPage />);
    confirmLeave.mockReturnValueOnce(false);
    fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
    expect(push).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
    expect(push).toHaveBeenCalledWith("/dashboard/blog-posts");
  });

  // Scenario: A concurrent save conflict is surfaced
  it("shows the conflict message and keeps the editor", () => {
    editorState.mockReturnValue(
      state({
        dirty: true,
        error: { kind: "version_conflict", detail: "version_conflict" },
      }),
    );
    render(<BlogPostEditPage />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Your unsaved text is kept here",
    );
    expect(screen.getAllByText(/^Section \d$/)).toHaveLength(3);
  });

  // Scenario: A non-migrated row shows a blocking migration banner
  it("shows the migration banner instead of the editor for a legacy row", () => {
    editorState.mockReturnValue(state({ draft: null, validation: null }));
    render(<BlogPostEditPage />);
    expect(screen.getByTestId("migration-pending-banner")).toBeInTheDocument();
    expect(screen.queryByText(/^Section \d$/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
  });

  it("shows the migration banner with the API error after a refused write", () => {
    editorState.mockReturnValue(
      state({
        error: { kind: "migration_pending", detail: "blog_document_not_v2" },
      }),
    );
    render(<BlogPostEditPage />);
    expect(screen.getByText("blog_document_not_v2")).toBeInTheDocument();
  });

  // Scenario: An empty title cannot be saved
  it("shows field errors", () => {
    editorState.mockReturnValue(
      state({
        validation: {
          title: "titleRequired",
          excerpt: "excerptTooLong",
          document: {},
        },
      }),
    );
    render(<BlogPostEditPage />);
    expect(screen.getByText("The title is required.")).toBeInTheDocument();
    expect(
      screen.getByText("The excerpt can have at most 500 characters."),
    ).toBeInTheDocument();
  });

  it("forwards title, excerpt and section edits into the draft", () => {
    const updateDraft = vi.fn();
    editorState.mockReturnValue(state({ updateDraft }));
    render(<BlogPostEditPage />);
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Novo" },
    });
    fireEvent.change(screen.getByLabelText("Excerpt"), {
      target: { value: "Resumo" },
    });
    fireEvent.change(screen.getAllByLabelText("Heading")[0], {
      target: { value: "H" },
    });
    const draft = { title: "x", excerpt: "", document: v2Document() };
    const results = updateDraft.mock.calls.map(([edit]) =>
      (edit as (d: typeof draft) => typeof draft)(draft),
    );
    expect(results[0].title).toBe("Novo");
    expect(results[1].excerpt).toBe("Resumo");
    expect(results[2].document.sections[0].heading).toBe("H");
  });

  it("applies an AI suggestion to the selected section text", () => {
    const updateDraft = vi.fn();
    editorState.mockReturnValue(state({ updateDraft }));
    render(<BlogPostEditPage />);
    const body = screen.getAllByLabelText(
      "Body (markdown)",
    )[0] as HTMLTextAreaElement;
    body.setSelectionRange(0, 5);
    fireEvent.select(body);
    capturedApply?.("Texto");
    const draft = { title: "x", excerpt: "", document: v2Document() };
    const edit = updateDraft.mock.calls.at(-1)?.[0] as (
      d: typeof draft,
    ) => typeof draft;
    expect(
      edit(draft).document.sections.find((s) => s.id === SEC_1)?.body_md,
    ).toBe("Texto um");
  });

  it("shows a load error and not-found", () => {
    editorState.mockReturnValue(state({ post: undefined, loadFailed: true }));
    const { rerender } = render(<BlogPostEditPage />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not load this post",
    );
    editorState.mockReturnValue(state({ post: undefined }));
    rerender(<BlogPostEditPage />);
    expect(screen.getByText("Blog post not found.")).toBeInTheDocument();
  });

  // AE-0424 review: workflow controls wait for a running slot action.
  it("disables the review controls while a slot action runs", () => {
    slotsPending.mockReturnValue(true);
    editorState.mockReturnValue(
      state({ post: blogPost({ status: "under_review" }) }),
    );
    render(<BlogPostEditPage />);
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    slotsPending.mockReturnValue(false);
  });

  it("shows a spinner while loading", () => {
    editorState.mockReturnValue(state({ post: undefined, loading: true }));
    const { container } = render(<BlogPostEditPage />);
    expect(container.querySelector(".h-64")).not.toBeNull();
  });

  // AE-0425 review fix 2: the run owns the document while it generates.
  it("is read-only while the generation is in progress", () => {
    const generating = {
      ...blogPost(),
      ai_generation_metadata: { generation: { status: "in_progress" } },
    };
    editorState.mockReturnValue(state({ post: generating, dirty: true }));
    render(<BlogPostEditPage />);
    expect(screen.getByTestId("blog-editor-fields")).toBeDisabled();
    expect(screen.getByLabelText("Title")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
  });

  it("is editable once the generation has finished", () => {
    const done = {
      ...blogPost(),
      ai_generation_metadata: { generation: { status: "complete" } },
    };
    editorState.mockReturnValue(state({ post: done, dirty: true }));
    render(<BlogPostEditPage />);
    expect(screen.getByTestId("blog-editor-fields")).not.toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Save changes" }),
    ).not.toBeDisabled();
  });

  // AE-0425 follow-up: the banner's Retry knows about unsaved edits.
  it("tells the generation banner when the draft has unsaved edits", () => {
    editorState.mockReturnValue(state({ dirty: true }));
    const { rerender } = render(<BlogPostEditPage />);
    expect(capturedUnsaved).toBe(true);
    editorState.mockReturnValue(state({ dirty: false }));
    rerender(<BlogPostEditPage />);
    expect(capturedUnsaved).toBe(false);
  });
});
