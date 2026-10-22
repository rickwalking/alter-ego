import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CreateUserDialog } from "./create-user-dialog";

const TYPED_PASSWORD = "Sup3r-Secret-Pass!";
const PASSWORD_LABEL = /^Password/;

function renderDialog() {
  render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
  return screen.getByLabelText(PASSWORD_LABEL);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("create-user password field", () => {
  // Scenario: The create-user password is masked by default
  it("renders a new-password input that is masked", () => {
    const input = renderDialog();

    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autocomplete", "new-password");
    const toggle = screen.getByRole("button", { name: "Show password" });
    expect(toggle).not.toHaveAttribute("aria-pressed");
    expect(toggle).toHaveAttribute("aria-controls", input.id);
    expect(toggle).toHaveAttribute("type", "button");
  });

  // Scenario: The admin can show and hide the typed password
  it("shows and hides the typed password on demand", async () => {
    const user = userEvent.setup();
    const input = renderDialog();
    await user.type(input, TYPED_PASSWORD);

    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveValue(TYPED_PASSWORD);

    await user.click(screen.getByRole("button", { name: "Hide password" }));
    expect(input).toHaveAttribute("type", "password");
    expect(
      screen.getByRole("button", { name: "Show password" }),
    ).toBeInTheDocument();
  });

  // Scenario: A typed password is never echoed back
  it("does not echo a typed password in the success message", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "u1", email: "new@example.com" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const input = renderDialog();
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Full name"), "New User");
    await user.type(input, TYPED_PASSWORD);

    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(
        screen.getByText("User created successfully."),
      ).toBeInTheDocument();
    });
    expect(document.body.textContent).not.toContain(TYPED_PASSWORD);
    const body = JSON.parse(
      (fetchMock.mock.calls[0] as [string, RequestInit])[1].body as string,
    ) as { password?: string };
    expect(body.password).toBe(TYPED_PASSWORD);
  });
});
