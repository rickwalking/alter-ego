import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NotificationCenter } from "@/modules/editorial/workflow/components/notification-center";
import type { NotificationItem } from "@/modules/editorial/workflow/types";

// Feature: Dashboard dates follow the active locale (AE-0417)
// tests/features/dashboard-locale-dates-ae0417.feature

vi.mock("next-intl", () => ({
  useLocale: () => "pt",
  useTranslations: () => (key: string) => key,
}));

const NOTIFICATION: NotificationItem = {
  id: "n-1",
  user_id: "u-1",
  notification_type: "review_requested",
  title: "Revisão pendente",
  body: null,
  status: "unread",
  content_id: null,
  content_type: null,
  deadline_at: null,
  created_at: new Date(2026, 9, 17, 14, 5).toISOString(),
};

vi.mock("@/modules/editorial/workflow/hooks/use-notifications", () => ({
  useNotifications: () => ({
    notifications: [NOTIFICATION],
    unreadCount: 1,
    loading: false,
    markRead: vi.fn(),
  }),
}));

describe("NotificationCenter (AE-0417)", () => {
  // Scenario: Workflow notifications show their time in the active locale
  it("shows the notification time in the active locale", () => {
    render(<NotificationCenter />);
    fireEvent.click(screen.getByRole("button", { name: "ariaLabel" }));
    expect(screen.getByText("Revisão pendente")).toBeInTheDocument();
    expect(screen.getByText("17/10/2026, 14:05")).toBeInTheDocument();
  });
});
