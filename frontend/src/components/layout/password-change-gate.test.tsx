/**
 * Gherkin: tests/features/change-own-password-ae0511.feature
 */
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PasswordChangeGate } from "./password-change-gate";

const replace = vi.fn();
const navigation = vi.hoisted(() => ({ pathname: "/dashboard/chat" }));
const session = vi.hoisted(() => ({
  user: null as null | { must_change_password: boolean },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => navigation.pathname,
}));

vi.mock("@/modules/identity", () => ({
  useAuth: () => ({ user: session.user }),
}));

const CHANGE_PAGE = "/dashboard/account/password";

function renderGate(): void {
  render(
    <PasswordChangeGate>
      <p>page content</p>
    </PasswordChangeGate>,
  );
}

beforeEach(() => {
  replace.mockReset();
  navigation.pathname = "/dashboard/chat";
});

describe("PasswordChangeGate", () => {
  // Scenario: A user with a temporary password is sent to the change-password page
  it.each(["/dashboard/chat", "/admin/users"])(
    "sends a flagged user from %s to the change-password page",
    (pathname) => {
      navigation.pathname = pathname;
      session.user = { must_change_password: true };

      renderGate();

      expect(screen.queryByText("page content")).not.toBeInTheDocument();
      expect(replace).toHaveBeenCalledWith(CHANGE_PAGE);
    },
  );

  // Scenario: The change-password page explains a forced change
  it("lets a flagged user see the change-password page", () => {
    navigation.pathname = CHANGE_PAGE;
    session.user = { must_change_password: true };

    renderGate();

    expect(screen.getByText("page content")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  // Scenario: A user changes their password from the dashboard
  it.each([{ must_change_password: false }, null])(
    "renders the page for %o",
    (user) => {
      session.user = user;

      renderGate();

      expect(screen.getByText("page content")).toBeInTheDocument();
      expect(replace).not.toHaveBeenCalled();
    },
  );
});
