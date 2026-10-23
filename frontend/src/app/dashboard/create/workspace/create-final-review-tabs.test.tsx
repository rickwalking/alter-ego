import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { ApiError } from "@/lib/api-client";
import type { EditorialWorkflowState } from "@/modules/publishing";

/** Gherkin: tests/features/final-review-copy-edit-ae0505.feature. */

const m = vi.hoisted(() => ({
  saveCopy: vi.fn(),
  refetchProject: vi.fn(() => Promise.resolve()),
  project: { current: undefined as Record<string, unknown> | undefined },
  projectError: { current: false },
  fetch: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: m.push }),
}));
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: m.fetch,
}));
vi.mock(
  "@/modules/publishing/distribution/hooks/use-save-carousel-copy",
  () => ({
    useSaveCarouselCopy: () => ({ mutateAsync: m.saveCopy }),
  }),
);
vi.mock("@/modules/publishing/distribution/hooks/use-copy-versions", () => ({
  useCarouselCopyVersions: () => ({ data: undefined, isLoading: false }),
  useRestoreCopyVersion: () => ({ mutateAsync: vi.fn() }),
}));
vi.mock("@/modules/editorial", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/editorial")>()),
  useCarouselProject: () => ({
    data: m.project.current,
    isError: m.projectError.current,
    refetch: m.refetchProject,
  }),
}));
vi.mock(
  "@/app/dashboard/create/workspace/phase-review/content-phase-review",
  () => ({ ContentPhaseReview: () => <div>slides</div> }),
);

import { CreateFinalReviewTabs } from "./create-final-review-tabs";

const PROJECT_ID = "proj-1";
const SAVED_CAPTION = "Legenda salva na página de publicação";
const CHECKPOINT_CAPTION = "Legenda gerada no checkpoint";
const CAPTION_LABEL = "Instagram caption (PT)";

function workflowState(): EditorialWorkflowState {
  return {
    project_id: PROJECT_ID,
    current_phase: "final_review",
    phase_status: "awaiting_human",
    lock_version: 5,
    caption: CHECKPOINT_CAPTION,
    linkedin_post_pt: "Post PT do checkpoint",
    linkedin_post_en: "Checkpoint EN post",
  } as EditorialWorkflowState;
}

function savedProject(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    id: PROJECT_ID,
    caption: SAVED_CAPTION,
    linkedin_post_pt: "Post PT salvo",
    linkedin_post_en: "Saved EN post",
    ...overrides,
  };
}

function renderTabs(
  onCopySaved = vi.fn(() => Promise.resolve()),
  onCopyBusyChange = vi.fn(),
): {
  onCopySaved: typeof onCopySaved;
  onCopyBusyChange: typeof onCopyBusyChange;
} {
  const client = new QueryClient();
  const ui: ReactElement = (
    <QueryClientProvider client={client}>
      <CreateFinalReviewTabs
        projectId={PROJECT_ID}
        state={workflowState()}
        onCopySaved={onCopySaved}
        onCopyBusyChange={onCopyBusyChange}
      />
    </QueryClientProvider>
  );
  render(ui);
  return { onCopySaved, onCopyBusyChange };
}

async function openTab(name: string): Promise<void> {
  await userEvent.setup().click(screen.getByRole("tab", { name }));
}

async function replaceText(label: string, text: string): Promise<void> {
  const user = userEvent.setup();
  const field = screen.getByLabelText(label);
  await user.clear(field);
  await user.type(field, text);
}

beforeEach(() => {
  m.saveCopy.mockReset();
  m.saveCopy.mockResolvedValue({ lock_version: 6 });
  m.refetchProject.mockClear();
  m.fetch.mockReset();
  m.push.mockReset();
  m.project.current = savedProject();
  m.projectError.current = false;
});

function blogResponses(preview: Response): void {
  m.fetch.mockImplementation((url: string) =>
    Promise.resolve(
      url.includes("from-carousel")
        ? new Response(
            JSON.stringify({
              code: "blog_post_exists_for_project",
              post_id: "post-9",
            }),
            { status: 409 },
          )
        : preview,
    ),
  );
}

describe("CreateFinalReviewTabs copy editing (AE-0505)", () => {
  /** Scenario: The reviewer saves an edited caption in the final review */
  it("saves the edited caption with the workflow lock version", async () => {
    renderTabs();
    await openTab("Caption");
    await replaceText(CAPTION_LABEL, "Nova legenda");
    await userEvent.setup().click(screen.getByRole("button", { name: "Save" }));
    expect(m.saveCopy).toHaveBeenCalledWith({
      projectId: PROJECT_ID,
      lockVersion: 5,
      texts: { caption: "Nova legenda" },
    });
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  /** Scenario: The reviewer saves a LinkedIn post per language */
  it("saves only the edited English LinkedIn post", async () => {
    renderTabs();
    await openTab("LinkedIn");
    await userEvent.setup().click(screen.getByRole("tab", { name: "en" }));
    await replaceText("LinkedIn post (EN)", "Edited EN post");
    await userEvent.setup().click(screen.getByRole("button", { name: "Save" }));
    expect(m.saveCopy).toHaveBeenCalledWith({
      projectId: PROJECT_ID,
      lockVersion: 5,
      texts: { linkedin_post_en: "Edited EN post" },
    });
  });

  /** Scenario: The final review shows the saved project text */
  it("shows the saved project caption over the checkpoint one", async () => {
    renderTabs();
    await openTab("Caption");
    expect(screen.getByLabelText(CAPTION_LABEL)).toHaveValue(SAVED_CAPTION);
  });

  /** Scenario: The checkpoint text is shown when the project has none */
  it("falls back to the checkpoint caption when the project has none", async () => {
    m.project.current = savedProject({ caption: null });
    renderTabs();
    await openTab("Caption");
    expect(screen.getByLabelText(CAPTION_LABEL)).toHaveValue(
      CHECKPOINT_CAPTION,
    );
  });

  /** Scenario: The checkpoint text is shown when the project has none */
  it("waits for the saved texts before showing an editor", async () => {
    m.project.current = undefined;
    renderTabs();
    await openTab("Caption");
    expect(screen.getByText("Loading the saved texts…")).toBeInTheDocument();
    expect(screen.queryByLabelText(CAPTION_LABEL)).not.toBeInTheDocument();
  });

  /** Scenario: A save refreshes the workflow state and the project */
  it("refetches the workflow state and the project after a save", async () => {
    const { onCopySaved } = renderTabs();
    await openTab("Caption");
    await replaceText(CAPTION_LABEL, "Outra legenda");
    await userEvent.setup().click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onCopySaved).toHaveBeenCalledTimes(1));
    expect(m.refetchProject).toHaveBeenCalledTimes(1);
  });

  /** Scenario: A stale save explains itself and refetches */
  it("explains a stale save, keeps the text and refetches", async () => {
    const stale = new ApiError(409, "Conflict");
    stale.detail = "version_conflict";
    m.saveCopy.mockRejectedValue(stale);
    const { onCopySaved } = renderTabs();
    await openTab("Caption");
    await replaceText(CAPTION_LABEL, "Legenda atrasada");
    await userEvent.setup().click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onCopySaved).toHaveBeenCalledTimes(1));
    expect(m.refetchProject).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status")).toHaveTextContent(
      "This carousel changed since the page opened.",
    );
    expect(screen.getByLabelText(CAPTION_LABEL)).toHaveValue(
      "Legenda atrasada",
    );
  });

  /** Scenario: Switching tabs keeps unsaved drafts */
  it("keeps an unsaved caption across a tab switch", async () => {
    renderTabs();
    await openTab("Caption");
    await replaceText(CAPTION_LABEL, "Rascunho não salvo");
    await openTab("LinkedIn");
    await openTab("Caption");
    expect(screen.getByLabelText(CAPTION_LABEL)).toHaveValue(
      "Rascunho não salvo",
    );
  });

  /** Scenario: The blog body is edited in the blog editor */
  it("opens the carousel's existing blog post in the blog editor", async () => {
    blogResponses(
      new Response(JSON.stringify({ markdown: "# Blog" }), { status: 200 }),
    );
    renderTabs();
    await openTab("Blog");
    expect(await screen.findByText("# Blog")).toBeInTheDocument();
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Open in the blog editor" }));
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Open or generate the post" }));
    await waitFor(() =>
      expect(m.push).toHaveBeenCalledWith("/dashboard/blog-posts/post-9/edit"),
    );
  });

  /** Scenario: The blog editor waits for unsaved caption or LinkedIn edits */
  it("keeps the blog editor closed while a caption edit is unsaved", async () => {
    blogResponses(
      new Response(JSON.stringify({ markdown: "# Blog" }), { status: 200 }),
    );
    renderTabs();
    await openTab("Caption");
    await replaceText(CAPTION_LABEL, "Rascunho");
    await openTab("Blog");
    expect(
      screen.getByRole("button", { name: "Open in the blog editor" }),
    ).toBeDisabled();
    expect(
      screen.getByText(
        "Save or discard the caption or LinkedIn edit before opening the blog editor.",
      ),
    ).toBeInTheDocument();
  });

  /** Scenario: The blog preview or the blog editor cannot be opened */
  it("says so when the blog preview cannot be loaded", async () => {
    blogResponses(new Response("{}", { status: 500 }));
    renderTabs();
    await openTab("Blog");
    expect(
      await screen.findByText("Could not load draft blog preview."),
    ).toBeInTheDocument();
  });

  /** Scenario: A save refused for another reason explains why */
  it("explains a refused save of a published caption", async () => {
    const published = new ApiError(409, "Conflict");
    published.detail = "caption_published";
    m.saveCopy.mockRejectedValue(published);
    const { onCopySaved } = renderTabs();
    await openTab("Caption");
    await replaceText(CAPTION_LABEL, "Legenda tarde");
    await userEvent.setup().click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "The caption is already published on Instagram",
    );
    expect(onCopySaved).not.toHaveBeenCalled();
    expect(screen.getByLabelText(CAPTION_LABEL)).toHaveValue("Legenda tarde");
  });

  /** Scenario: The saved texts cannot be loaded */
  it("offers a retry when the saved texts cannot be loaded", async () => {
    m.project.current = undefined;
    m.projectError.current = true;
    renderTabs();
    await openTab("LinkedIn");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not load the saved texts.",
    );
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Try again" }));
    expect(m.refetchProject).toHaveBeenCalledTimes(1);
  });

  /** Scenario: Leaving the review with unsaved edits asks first */
  it("guards in-app links while a review edit is unsaved", async () => {
    renderTabs();
    await openTab("Caption");
    await replaceText(CAPTION_LABEL, "Rascunho");
    const link = document.createElement("a");
    link.href = "/dashboard";
    link.textContent = "away";
    document.body.appendChild(link);
    await userEvent.setup().click(link);
    expect(screen.getByText("Leave without saving?")).toBeInTheDocument();
    link.remove();
  });

  /** Scenario: Approve and send back wait for unsaved or saving texts */
  it("reports the texts busy while unsaved or saving, idle once saved", async () => {
    let finishRefresh: () => void = () => undefined;
    const onCopySaved = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishRefresh = resolve;
        }),
    );
    const { onCopyBusyChange } = renderTabs(onCopySaved);
    expect(onCopyBusyChange).toHaveBeenLastCalledWith(false);
    await openTab("Caption");
    await replaceText(CAPTION_LABEL, "Nova");
    expect(onCopyBusyChange).toHaveBeenLastCalledWith(true);
    await userEvent.setup().click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onCopySaved).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
    expect(onCopyBusyChange).toHaveBeenLastCalledWith(true);
    finishRefresh();
    await waitFor(() =>
      expect(onCopyBusyChange).toHaveBeenLastCalledWith(false),
    );
    expect(screen.getByText("Saved.")).toBeInTheDocument();
  });
});
