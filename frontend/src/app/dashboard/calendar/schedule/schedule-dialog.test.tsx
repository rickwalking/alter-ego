/**
 * Scenarios: tests/features/calendar-schedule-post.feature.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { CalendarItem } from "@/modules/editorial";
import type { BlogPost } from "@/modules/publishing";

const mocks = vi.hoisted(() => ({
  posts: [] as BlogPost[],
  allPosts: [] as BlogPost[],
  calendarItems: [] as CalendarItem[],
  loading: false,
  error: null as string | null,
  request: vi.fn(),
  calendar: vi.fn(),
}));

vi.mock("@/modules/publishing", () => ({
  useBlogPosts: (filters: { status?: string }) => ({
    posts: filters.status === "approved" ? mocks.posts : mocks.allPosts,
    loading: mocks.loading,
    error: mocks.error,
  }),
}));
vi.mock("@/modules/editorial", () => ({
  useContentCalendar: (start?: string, end?: string, enabled?: boolean) => {
    mocks.calendar(start, end, enabled);
    return {
      calendar: enabled
        ? { items: mocks.calendarItems, start, end, total: 0 }
        : null,
    };
  },
}));
vi.mock("./schedule-request", () => ({ requestSchedule: mocks.request }));

import { ScheduleDialog } from "./schedule-dialog";

const ORIGINAL_TZ = process.env.TZ;

function restoreTimeZone(): void {
  if (ORIGINAL_TZ === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = ORIGINAL_TZ;
  }
}
const LAUNCH = {
  id: "p1",
  title: "Launch",
  status: "approved",
  lock_version: 3,
} as BlogPost;
const OTHER = {
  id: "p2",
  title: "Other",
  status: "approved",
  lock_version: 1,
} as BlogPost;
const DRAFT = {
  id: "p3",
  title: "Ideas",
  status: "draft",
  lock_version: 1,
} as BlogPost;
const PUBLISHED = {
  id: "p4",
  title: "Old news",
  status: "published",
  lock_version: 1,
} as BlogPost;
const OTHER_ON_CALENDAR: CalendarItem = {
  id: "p2",
  content_type: "blog_post",
  title: "Other",
  status: "approved",
  event_date: "2026-10-24T00:00:00+00:00",
  is_scheduled: true,
};

function renderDialog() {
  const onClose = vi.fn();
  const onScheduled = vi.fn();
  render(<ScheduleDialog open onClose={onClose} onScheduled={onScheduled} />);
  return { onClose, onScheduled, user: userEvent.setup() };
}

async function fill(
  user: ReturnType<typeof userEvent.setup>,
  postId: string,
  time: string,
): Promise<void> {
  await user.selectOptions(screen.getByLabelText("Post"), postId);
  const field = screen.getByLabelText("Publish at");
  await user.clear(field);
  await user.type(field, time);
}

describe("ScheduleDialog", () => {
  beforeEach(() => {
    process.env.TZ = "America/Sao_Paulo";
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-22T13:00:00.000Z"));
    mocks.posts = [LAUNCH, OTHER];
    mocks.allPosts = [LAUNCH, OTHER, DRAFT, PUBLISHED];
    mocks.calendarItems = [];
    mocks.calendar.mockClear();
    mocks.loading = false;
    mocks.error = null;
    mocks.request.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    restoreTimeZone();
  });

  it("renders nothing while closed", () => {
    const { container } = render(
      <ScheduleDialog open={false} onClose={vi.fn()} onScheduled={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  // Scenario: Schedule Post opens a dialog listing the approved blog posts
  it("lists the approved posts in a named dialog", () => {
    renderDialog();
    const dialog = screen.getByRole("dialog", { name: "Schedule a blog post" });
    const options = within(dialog).getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      "Choose an approved post",
      "Launch",
      "Other",
      "Ideas — approve it first",
    ]);
  });

  // Scenario: Drafts are listed but must be approved first
  it("lists drafts disabled with an approve-first note", () => {
    renderDialog();
    expect(screen.getByRole("option", { name: "Launch" })).toBeEnabled();
    expect(
      screen.getByRole("option", { name: "Ideas — approve it first" }),
    ).toBeDisabled();
    expect(
      screen.queryByRole("option", { name: /Old news/ }),
    ).not.toBeInTheDocument();
  });

  // Scenario: The dialog says when there is nothing to schedule
  it("explains an empty list and links to the blog posts", () => {
    mocks.posts = [];
    mocks.allPosts = [PUBLISHED];
    renderDialog();
    expect(
      screen.getByText(/There are no approved blog posts to schedule\./),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open blog posts" }),
    ).toHaveAttribute("href", "/dashboard/blog-posts");
    expect(screen.getByRole("button", { name: "Schedule" })).toBeDisabled();
  });

  it("shows a spinner while loading and an error when loading failed", () => {
    mocks.loading = true;
    const { unmount } = render(
      <ScheduleDialog open onClose={vi.fn()} onScheduled={vi.fn()} />,
    );
    expect(screen.queryByLabelText("Post")).not.toBeInTheDocument();
    unmount();
    mocks.loading = false;
    mocks.error = "Failed to fetch blog posts";
    renderDialog();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not load the approved posts.",
    );
  });

  // Scenario: The time is entered in the viewer's timezone
  it("names the viewer's timezone and starts a minute from now", () => {
    renderDialog();
    const field = screen.getByLabelText("Publish at");
    expect(field).toHaveAccessibleDescription(
      "Times are in your timezone: America/Sao_Paulo",
    );
    expect(field).toHaveAttribute("min", "2026-10-22T10:01");
  });

  // Scenario: A post and a time are required
  it("requires a post and then a time before sending", async () => {
    const { user } = renderDialog();
    await user.click(screen.getByRole("button", { name: "Schedule" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a post.");
    await user.selectOptions(screen.getByLabelText("Post"), "p1");
    await user.click(screen.getByRole("button", { name: "Schedule" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Choose a date and time.",
    );
    expect(mocks.request).not.toHaveBeenCalled();
  });

  // Scenario: A time in the past is refused before sending
  it("refuses a past time before sending", async () => {
    const { user } = renderDialog();
    await fill(user, "p1", "2026-10-22T09:00");
    await user.click(screen.getByRole("button", { name: "Schedule" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Choose a time at least a minute from now.",
    );
    expect(mocks.request).not.toHaveBeenCalled();
  });

  // Scenario: The calendar refreshes and confirms the schedule
  it("sends the chosen post and local time and reports success", async () => {
    const scheduled = { ...LAUNCH, scheduled_publish_at: "x" };
    mocks.request.mockResolvedValue({ ok: true, post: scheduled });
    const { user, onScheduled } = renderDialog();
    await fill(user, "p1", "2026-10-23T20:00");
    await user.click(screen.getByRole("button", { name: "Schedule" }));
    const [post, at] = mocks.request.mock.calls[0] as [BlogPost, Date];
    expect(post).toBe(LAUNCH);
    expect(at.toISOString()).toBe("2026-10-23T23:00:00.000Z");
    expect(onScheduled).toHaveBeenCalledWith(scheduled);
  });

  // Scenario: Another calendar item within an hour is flagged
  it("warns about a calendar item within an hour and still schedules", async () => {
    mocks.calendarItems = [OTHER_ON_CALENDAR];
    mocks.request.mockResolvedValue({ ok: true, post: LAUNCH });
    const { user, onScheduled } = renderDialog();
    await fill(user, "p1", "2026-10-23T20:00");
    expect(mocks.calendar).toHaveBeenLastCalledWith(
      "2026-10-23T22:00:00.000Z",
      "2026-10-24T00:00:00.000Z",
      true,
    );
    expect(
      screen.getByText(
        "Also on the calendar within an hour of this time: Other",
      ),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Schedule" }));
    expect(onScheduled).toHaveBeenCalled();
  });

  // Scenario: The post being scheduled is not its own conflict
  it("does not warn about the post being scheduled", async () => {
    mocks.calendarItems = [{ ...OTHER_ON_CALENDAR, id: "p1", title: "Launch" }];
    const { user } = renderDialog();
    await fill(user, "p1", "2026-10-23T20:00");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("reads no calendar until a time is chosen", () => {
    renderDialog();
    expect(mocks.calendar).toHaveBeenLastCalledWith(
      undefined,
      undefined,
      false,
    );
  });

  // Scenario: A post changed since the list loaded is reported
  it("shows the backend's refusal and keeps the dialog open", async () => {
    mocks.request.mockResolvedValue({ ok: false, error: "versionConflict" });
    const { user, onScheduled } = renderDialog();
    await fill(user, "p1", "2026-10-23T20:00");
    await user.click(screen.getByRole("button", { name: "Schedule" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "This post changed since the list loaded.",
    );
    expect(onScheduled).not.toHaveBeenCalled();
  });

  // Scenario: Cancel closes the dialog without scheduling
  it("closes on Cancel without sending", async () => {
    const { user, onClose } = renderDialog();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalled();
    expect(mocks.request).not.toHaveBeenCalled();
  });

  // Scenario: Keyboard focus stays in the dialog
  it("moves focus in, keeps Tab inside and closes on Escape", async () => {
    const { user, onClose } = renderDialog();
    const dialog = screen.getByRole("dialog");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    expect(screen.getByLabelText("Post")).toHaveFocus();
    screen.getByRole("button", { name: "Schedule" }).focus();
    await user.tab();
    expect(screen.getByLabelText("Post")).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
