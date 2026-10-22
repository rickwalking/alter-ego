import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useNotifications } from "./use-notifications";

const translate = (key: string): string => key;
vi.mock("next-intl", () => ({
  useTranslations: () => translate,
}));

const authenticatedFetch = vi.fn<(...args: unknown[]) => Promise<Response>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (...args: unknown[]) => authenticatedFetch(...args),
}));

const UNREAD = {
  id: "n-1",
  user_id: "u-1",
  notification_type: "review_requested",
  title: "Review",
  body: null,
  status: "unread",
  content_id: null,
  content_type: null,
  deadline_at: null,
  created_at: "2026-10-21T10:00:00Z",
};

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

describe("useNotifications mark as read", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("reports a failed mark-as-read instead of rejecting", async () => {
    // Scenario: A failed "mark as read" is shown in the notification panel
    authenticatedFetch.mockResolvedValueOnce(ok({ items: [UNREAD] }));
    const { result } = renderHook(() => useNotifications());
    await waitFor(() => expect(result.current.notifications).toHaveLength(1));

    authenticatedFetch.mockResolvedValueOnce(new Response("", { status: 500 }));
    await act(() => result.current.markRead("n-1"));

    expect(result.current.error).toBe("markReadFailed");
    expect(result.current.notifications[0]?.status).toBe("unread");
  });

  it("reports a network failure on mark-as-read", async () => {
    // Scenario: A failed "mark as read" is shown in the notification panel
    authenticatedFetch.mockResolvedValueOnce(ok({ items: [UNREAD] }));
    const { result } = renderHook(() => useNotifications());
    await waitFor(() => expect(result.current.notifications).toHaveLength(1));

    authenticatedFetch.mockRejectedValueOnce(new TypeError("offline"));
    await act(() => result.current.markRead("n-1"));

    expect(result.current.error).toBe("markReadFailed");
    expect(result.current.unreadCount).toBe(1);
  });

  it("marks the notification read on success", async () => {
    authenticatedFetch.mockResolvedValueOnce(ok({ items: [UNREAD] }));
    const { result } = renderHook(() => useNotifications());
    await waitFor(() => expect(result.current.notifications).toHaveLength(1));

    authenticatedFetch.mockResolvedValueOnce(ok({}));
    await act(() => result.current.markRead("n-1"));

    expect(result.current.error).toBeNull();
    expect(result.current.unreadCount).toBe(0);
  });
});
