/**
 * Gherkin: tests/features/change-own-password-ae0511.feature
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChangePasswordDialog } from "./change-password-dialog";

const USER = {
  id: "u1",
  email: "qa@example.com",
  full_name: "QA",
  role: "editor",
  is_active: true,
  created_at: "2026-04-28T00:00:00Z",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("reset-password dialog", () => {
  // Scenario: The reset dialog shows the temporary password once with a must-change note
  it("says before and after the reset that the user must change it", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ temp_password: "Temp-Pass-123!" })),
        ),
    );
    const user = userEvent.setup();
    render(
      <ChangePasswordDialog
        user={USER}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/the user must change it at the next sign-in/i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reset" }));

    expect(await screen.findByText("Temp-Pass-123!")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Copy it now: it will not be shown again. The user must change it at the next sign-in before using the app.",
    );
  });
});
