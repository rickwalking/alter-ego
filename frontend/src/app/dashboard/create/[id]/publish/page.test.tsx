/**
 * The carousel publish page, behaviour pinned before the page was split into
 * a hook and sections. Covers loading, not-found,
 * the readiness / failed / awaiting-approval notices, publishing to the site
 * and to Instagram, and the rebuild / republish cache-bust.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import DashboardCreatePublishPage from "./page";

const m = vi.hoisted(() => ({
  project: vi.fn<() => unknown>(),
  refetchProject: vi.fn(() => Promise.resolve(undefined)),
  refreshState: vi.fn(() => Promise.resolve(null)),
  workflowState: null as EditorialWorkflowState | null,
  fetch: vi.fn<(...args: unknown[]) => unknown>(),
  publishInstagram: vi.fn(),
  saveCopy: vi.fn(() => Promise.resolve({ lock_version: 8 })),
  republish: vi.fn(),
  ready: true,
  coverPicker: false,
  radar: false,
  blogHref: null as string | null,
  refetchBlogHref: vi.fn(() => Promise.resolve(undefined)),
}));

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "p1" }) }));
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));
vi.mock("@/components/atoms/neon-spinner", () => ({
  NeonSpinner: () => <div>spinner</div>,
}));
vi.mock("@/components/organisms/neon-top-bar", () => ({
  NeonTopBar: ({ title }: { title: string }) => <h2>{title}</h2>,
}));
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (...args: unknown[]) => m.fetch(...args),
}));
vi.mock("@/app/dashboard/create/[id]/publish/publish-readiness", () => ({
  isPublishReady: () => m.ready,
  offersCoverPicker: () => m.coverPicker,
  offersRadarTemplates: () => m.radar,
}));
vi.mock("@/modules/editorial", () => ({
  useCarouselProject: () => m.project(),
  useEditorialWorkflow: () => ({
    refreshState: m.refreshState,
    state: m.workflowState,
  }),
  resolveLocalizedSlides: () => [{ slide_index: 1 }, { slide_index: 2 }],
  AutoRepairButton: ({
    onRepaired,
    onRepublishNeeded,
  }: {
    onRepaired: () => void;
    onRepublishNeeded: () => void;
  }) => (
    <div>
      <button type="button" onClick={onRepaired}>
        repaired
      </button>
      <button type="button" onClick={onRepublishNeeded}>
        republish-needed
      </button>
    </div>
  ),
}));
vi.mock(
  "@/modules/publishing/distribution/hooks/use-save-carousel-copy",
  () => ({
    useSaveCarouselCopy: () => ({ mutateAsync: m.saveCopy }),
  }),
);
vi.mock("@/modules/publishing", async () => ({
  useCopySave: (
    await vi.importActual<
      typeof import("@/modules/publishing/distribution/hooks/use-copy-save")
    >("@/modules/publishing/distribution/hooks/use-copy-save")
  ).useCopySave,
  mergePublishProjectWithWorkflow: (project: unknown) => project,
  usePublishInstagram: () => ({
    mutateAsync: m.publishInstagram,
    isPending: false,
  }),
  useRepublishCarousel: () => ({ mutate: m.republish }),
  useCarouselPublicPostHref: () => ({
    href: m.blogHref,
    refetch: m.refetchBlogHref,
  }),
  PublishPanel: ({
    onPublishInstagram,
    publishResult,
    cacheBustToken,
    slideNumbers,
    onSaveCopy,
  }: {
    onPublishInstagram?: (caption: string) => Promise<void>;
    onSaveCopy?: (texts: { caption: string }) => Promise<void>;
    publishResult: { status: string; message?: string };
    cacheBustToken?: string;
    slideNumbers: number[];
  }) => (
    <div>
      <span>
        result:{publishResult.status}:{publishResult.message ?? ""}
      </span>
      <span>bust:{cacheBustToken ?? "none"}</span>
      <span>slides:{slideNumbers.join(",")}</span>
      {onSaveCopy ? (
        <button type="button" onClick={() => void onSaveCopy({ caption: "c" })}>
          save-copy
        </button>
      ) : null}
      {onPublishInstagram ? (
        <button type="button" onClick={() => void onPublishInstagram("cap")}>
          publish-instagram
        </button>
      ) : null}
    </div>
  ),
  PublishFailedNotice: ({ workspaceHref }: { workspaceHref: string }) => (
    <div>failed-notice:{workspaceHref}</div>
  ),
  CoverPickerSection: () => <div>cover-picker</div>,
  RebuildPdfSection: ({
    onRebuilt,
  }: {
    onRebuilt: (version: string | null) => void;
  }) => (
    <button type="button" onClick={() => onRebuilt("v9")}>
      rebuild
    </button>
  ),
  SlideTextEditSection: ({
    runInProgress,
    rebuildPending,
  }: {
    runInProgress: boolean;
    rebuildPending: boolean;
  }) => (
    <div>
      slide-edit:{String(runInProgress)}:{String(rebuildPending)}
    </div>
  ),
  CreateBlogFromCarousel: ({ isPublic }: { isPublic: boolean }) => (
    <div>blog-from-carousel:{String(isPublic)}</div>
  ),
  RegenerateStrategySection: () => <div>regenerate-strategy</div>,
}));

const project = {
  id: "p1",
  topic: "AI topic",
  title: "",
  audience: "devs",
  niche: "tech",
  caption: "has caption",
  is_public: true,
  needs_republish_since: null,
};

function state(
  overrides: Partial<EditorialWorkflowState> = {},
): EditorialWorkflowState {
  return {
    project_id: "p1",
    current_phase: "final_review",
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "draft",
    ...overrides,
  };
}

const approved = (): EditorialWorkflowState =>
  state({ workflow_status: EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH });

function setProject(data: unknown, isLoading = false): void {
  m.project.mockReturnValue({
    data,
    isLoading,
    refetch: m.refetchProject,
  });
}

async function renderLoaded(): Promise<void> {
  render(<DashboardCreatePublishPage />);
  await waitFor(() =>
    expect(screen.queryByText("spinner")).not.toBeInTheDocument(),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  m.workflowState = state();
  m.ready = true;
  m.coverPicker = false;
  m.radar = false;
  setProject(project);
});

describe("DashboardCreatePublishPage", () => {
  it("shows a spinner while the project loads", () => {
    setProject(undefined, true);
    render(<DashboardCreatePublishPage />);
    expect(screen.getByText("spinner")).toBeInTheDocument();
  });

  it("waits for the workflow state before deciding (AE-0415 B25)", async () => {
    render(<DashboardCreatePublishPage />);
    expect(screen.getByText("spinner")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText("pageTitle")).toBeInTheDocument(),
    );
    expect(m.refreshState).toHaveBeenCalled();
  });

  it("shows not-found without a project", () => {
    setProject(undefined);
    render(<DashboardCreatePublishPage />);
    expect(screen.getByText("notFound")).toBeInTheDocument();
  });

  it("says the artifacts are not ready yet", async () => {
    m.ready = false;
    await renderLoaded();
    expect(screen.getByTestId("publish-not-ready")).toBeInTheDocument();
    expect(screen.queryByText(/^result:/)).not.toBeInTheDocument();
  });

  it("shows the failed notice instead of not-ready", async () => {
    m.ready = false;
    m.workflowState = state({ phase_status: WORKFLOW_PHASE_STATUS.FAILED });
    await renderLoaded();
    expect(
      screen.getByText("failed-notice:/dashboard/create/p1?step=outline"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("publish-not-ready")).not.toBeInTheDocument();
  });

  it("awaits the final approval before any publish", async () => {
    await renderLoaded();
    expect(screen.getByText("awaitingFinalApproval")).toBeInTheDocument();
    expect(screen.queryByText("publishToSite")).not.toBeInTheDocument();
    expect(screen.queryByText("publish-instagram")).not.toBeInTheDocument();
    expect(screen.getByText("slides:1,2")).toBeInTheDocument();
    expect(screen.getByText("AI topic")).toBeInTheDocument();
    expect(screen.getByText("blog-from-carousel:true")).toBeInTheDocument();
  });

  it("refetches the project when only the workflow has the caption", async () => {
    setProject({ ...project, caption: "" });
    m.workflowState = state({ caption: "new caption" });
    await renderLoaded();
    expect(m.refetchProject).toHaveBeenCalled();
  });

  /** Scenario: After a site publish the link opens the published blog post */
  it("publishes to the site and links the blog post", async () => {
    m.workflowState = approved();
    m.blogHref = "/blog/b1";
    m.fetch.mockResolvedValue({ ok: true });
    await renderLoaded();
    fireEvent.click(screen.getByText("publishToSite"));
    await waitFor(() =>
      expect(screen.getByText(/^sitePublished\s*$/)).toBeInTheDocument(),
    );
    expect(m.fetch).toHaveBeenCalledWith(
      expect.stringContaining("p1"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(m.refetchBlogHref).toHaveBeenCalled();
    expect(
      screen.getByRole("link", { name: "sitePublishedLink" }),
    ).toHaveAttribute("href", "/blog/b1");
  });

  /** Scenario: After a site publish without a blog post the link opens the public carousel */
  it("links the public carousel when there is no blog post", async () => {
    m.workflowState = approved();
    m.blogHref = null;
    m.fetch.mockResolvedValue({ ok: true });
    await renderLoaded();
    fireEvent.click(screen.getByText("publishToSite"));
    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "sitePublishedLink" }),
      ).toHaveAttribute("href", "/carousels/p1"),
    );
  });

  it("shows the server's reason when the site publish fails", async () => {
    m.workflowState = approved();
    m.fetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: "Not approved yet" }),
    });
    await renderLoaded();
    fireEvent.click(screen.getByText("publishToSite"));
    await waitFor(() =>
      expect(screen.getByText(/Not approved yet/)).toBeInTheDocument(),
    );
    /** Scenario: A failed site publish shows no link */
    expect(screen.queryByText("sitePublishedLink")).not.toBeInTheDocument();
  });

  it("falls back to a generic message on an unreadable failure", async () => {
    m.workflowState = approved();
    m.fetch.mockResolvedValue({
      ok: false,
      json: () => Promise.reject(new Error("not json")),
    });
    await renderLoaded();
    fireEvent.click(screen.getByText("publishToSite"));
    await waitFor(() =>
      expect(screen.getByText(/sitePublishFailed/)).toBeInTheDocument(),
    );
  });

  it.each([
    [{ status: "published" }, "result:success:instagram.published"],
    [{ status: "queued" }, "result:success:instagram.queued"],
    [{ status: "failed", error_message: "token" }, "result:error:token"],
    [{ status: "failed" }, "result:error:instagram.failed"],
  ])("reports the Instagram publish %j", async (answer, shown) => {
    m.workflowState = approved();
    m.publishInstagram.mockResolvedValue(answer);
    await renderLoaded();
    fireEvent.click(screen.getByText("publish-instagram"));
    await waitFor(() => expect(screen.getByText(shown)).toBeInTheDocument());
    expect(m.publishInstagram).toHaveBeenCalledWith({
      projectId: "p1",
      caption: "cap",
    });
  });

  it("reports a thrown Instagram publish", async () => {
    m.workflowState = approved();
    m.publishInstagram.mockRejectedValue(new Error("network"));
    await renderLoaded();
    fireEvent.click(screen.getByText("publish-instagram"));
    await waitFor(() =>
      expect(screen.getByText("result:error:network")).toBeInTheDocument(),
    );
  });

  it("cache-busts after a rebuild or a republish", async () => {
    m.republish.mockImplementation(
      (_vars: unknown, opts: { onSuccess: (data: unknown) => void }) =>
        opts.onSuccess({ artifact_version: "v10" }),
    );
    await renderLoaded();
    expect(screen.getByText("bust:none")).toBeInTheDocument();
    fireEvent.click(screen.getByText("rebuild"));
    expect(screen.getByText("bust:v9")).toBeInTheDocument();
    fireEvent.click(screen.getByText("republish-needed"));
    expect(screen.getByText("bust:v10")).toBeInTheDocument();
    fireEvent.click(screen.getByText("repaired"));
    expect(m.refetchProject).toHaveBeenCalled();
  });

  it("offers the cover picker, slide edits and radar templates", async () => {
    m.coverPicker = true;
    m.radar = true;
    m.workflowState = state({
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    });
    setProject({ ...project, needs_republish_since: "2026-10-01" });
    await renderLoaded();
    expect(screen.getByText("cover-picker")).toBeInTheDocument();
    expect(screen.getByText("regenerate-strategy")).toBeInTheDocument();
    expect(screen.getByText("slide-edit:true:true")).toBeInTheDocument();
  });

  /** Scenario: Saving the edited caption sends it with the loaded lock version */
  it("saves the panel texts at the workflow lock version", async () => {
    m.workflowState = state({ lock_version: 7 });
    await renderLoaded();
    fireEvent.click(screen.getByRole("button", { name: "save-copy" }));
    await waitFor(() => expect(m.refreshState).toHaveBeenCalledTimes(2));
    expect(m.saveCopy).toHaveBeenCalledWith({
      projectId: "p1",
      lockVersion: 7,
      texts: { caption: "c" },
    });
  });

  it("hides the workflow-bound sections without workflow state", async () => {
    m.coverPicker = true;
    m.workflowState = null;
    await renderLoaded();
    expect(screen.queryByText("cover-picker")).not.toBeInTheDocument();
    expect(screen.queryByText(/^slide-edit/)).not.toBeInTheDocument();
  });
});
