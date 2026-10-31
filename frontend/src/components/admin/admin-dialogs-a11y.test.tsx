/**
 * Gherkin: tests/features/users-area-polish-ae0514.feature
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CreateUserDialog } from "./create-user-dialog";
import { EditUserDialog } from "./edit-user-dialog";
import { UserTable } from "./user-table";

const USER = {
  id: "u1",
  email: "qa@example.com",
  full_name: "QA",
  role: "editor",
  is_active: true,
  created_at: "2026-04-28T00:00:00Z",
};

describe("admin user dialogs", () => {
  // Scenario: Admin user form fields have labels
  it("labels every create-user field", () => {
    render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(screen.getByLabelText("Email")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Full name")).toHaveAttribute("type", "text");
    expect(screen.getByLabelText("Role").tagName).toBe("SELECT");
    expect(screen.getByLabelText(/^Password/)).toHaveAttribute(
      "type",
      "password",
    );
  });

  // Scenario: Admin user form fields have labels
  it("labels the edit-user role field", () => {
    render(
      <EditUserDialog user={USER} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    expect(screen.getByLabelText("Role").tagName).toBe("SELECT");
  });

  // Scenario: Admin buttons and errors meet contrast
  it("uses the neon primary button (dark text on cyan) for submit", () => {
    render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
    const submit = screen.getByRole("button", { name: /create/i });
    expect(submit).toHaveClass("text-bg-deep");
    expect(submit).not.toHaveClass("bg-primary");
  });
});

describe("admin dialogs are real modals", () => {
  // Scenario: Every admin dialog is a real modal
  it.each([
    ["Edit", "dialog", "Edit user"],
    ["Reset password", "dialog", "Reset password"],
    ["Delete", "alertdialog", "Delete user"],
  ])(
    "the %s dialog is a labelled, modal %s with focus inside",
    async (action, role, title) => {
      const user = userEvent.setup();
      render(<UserTable users={[USER]} onRefresh={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: action }));

      const dialog = screen.getByRole(role, { name: title });
      expect(dialog).toHaveAttribute("aria-modal", "true");
      expect(dialog).toContainElement(document.activeElement as HTMLElement);
    },
  );

  // Scenario: Every admin dialog is a real modal
  it("the create dialog is a labelled modal dialog", () => {
    render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
    const dialog = screen.getByRole("dialog", { name: "Create user" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByLabelText("Email")).toHaveFocus();
  });

  // Scenario: Escape closes a dialog and focus returns to the opener
  it.each(["Edit", "Reset password", "Delete"])(
    "Escape closes the %s dialog and focus returns to its button",
    async (action) => {
      const user = userEvent.setup();
      render(<UserTable users={[USER]} onRefresh={vi.fn()} />);
      const opener = screen.getByRole("button", { name: action });

      await user.click(opener);
      expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
      await user.keyboard("{Escape}");

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
      expect(opener).toHaveFocus();
    },
  );

  // Scenario: Escape closes a dialog and focus returns to the opener
  it("Escape asks the create dialog to close", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<CreateUserDialog onClose={onClose} onSuccess={vi.fn()} />);

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledOnce();
  });

  // Scenario: Tab stays inside an open dialog
  it("Tab past the last button wraps to the first control", async () => {
    const user = userEvent.setup();
    render(<UserTable users={[USER]} onRefresh={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = screen.getByRole("alertdialog");
    const buttons = within(dialog)
      .getAllByRole("button")
      .filter((button) => button.getAttribute("aria-label") !== "Close dialog");

    buttons[buttons.length - 1]?.focus();
    await user.tab();

    expect(buttons[0]).toHaveFocus();
  });

  // Scenario: Every admin dialog is a real modal
  it("names the backdrop close button in the reader's language", () => {
    render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: "Close dialog" }),
    ).toBeInTheDocument();
  });
});
