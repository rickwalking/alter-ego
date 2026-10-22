import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CreateUserDialog } from "./create-user-dialog";
import { EditUserDialog } from "./edit-user-dialog";

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
  it("uses the darker primary shade for the submit button", () => {
    render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
    const submit = screen.getByRole("button", { name: /create/i });
    expect(submit).toHaveClass("bg-primary-700");
    expect(submit).not.toHaveClass("bg-primary");
  });
});
