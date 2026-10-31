/**
 * Gherkin: tests/features/users-area-polish-ae0514.feature
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChangePasswordDialog } from "./change-password-dialog";
import { DeleteUserDialog } from "./delete-user-dialog";

const USER = {
  id: "u1",
  email: "qa@example.com",
  full_name: "QA",
  role: "admin",
  is_active: true,
  created_at: "2026-04-28T00:00:00Z",
};

function stubFetch(body: unknown, status: number): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("delete dialog errors", () => {
  // Scenario: A last-admin or self-delete refusal is translated
  it.each([
    [
      { detail: "Cannot delete your own account", code: "self_delete" },
      "You cannot delete your own account.",
    ],
    [
      { detail: "Cannot delete the last admin", code: "last_admin" },
      "The last admin cannot be demoted, deactivated or deleted.",
    ],
    [{ detail: "Something else" }, "Failed to delete user."],
  ])("translates a 409 %o", async (body, message) => {
    stubFetch(body, 409);
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(
      <DeleteUserDialog user={USER} onClose={vi.fn()} onSuccess={onSuccess} />,
    );

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.queryByText(body.detail)).not.toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  // Scenario: An unknown create failure keeps the generic message
  it("keeps the generic message when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));
    const user = userEvent.setup();
    render(
      <DeleteUserDialog user={USER} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Failed to delete user.",
    );
  });

  // Scenario: Every admin dialog is a real modal
  it("closes and refreshes after a successful delete", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(
      <DeleteUserDialog user={USER} onClose={onClose} onSuccess={onSuccess} />,
    );

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(onSuccess).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });
});

describe("reset-password dialog", () => {
  // Scenario: A last-admin or self-delete refusal is translated
  it("translates a 404 into the user-gone message", async () => {
    stubFetch({ detail: "User with id u1 not found" }, 404);
    const user = userEvent.setup();
    render(
      <ChangePasswordDialog
        user={USER}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Reset" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This user no longer exists. Reload the list.",
    );
  });

  // Scenario: An unknown create failure keeps the generic message
  it("keeps the generic message when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));
    const user = userEvent.setup();
    render(
      <ChangePasswordDialog
        user={USER}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Reset" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Failed to reset password.",
    );
  });

  // Scenario: Row actions are large enough to tap
  it("shows the new password with a copy button and closes on Done", async () => {
    stubFetch({ temp_password: "Temp-Pass-123!" }, 200);
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(
      <ChangePasswordDialog
        user={USER}
        onClose={onClose}
        onSuccess={onSuccess}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Reset" }));

    expect(await screen.findByText("Temp-Pass-123!")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Password reset successfully.",
    );
    expect(screen.getByRole("button", { name: "Copy" })).toHaveClass(
      "min-h-11",
    );
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(onSuccess).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
