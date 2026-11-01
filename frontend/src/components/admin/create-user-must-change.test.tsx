/**
 * Gherkin: tests/features/create-user-must-change-ae0587.feature
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";

import { CreateUserDialog } from "./create-user-dialog";

const GENERATED_PASSWORD = "Gen3rated-Temp-42";
const TYPED_PASSWORD = "Sup3r-Secret-Pass!";
const FORM_NOTE = "The new user must change the password at the first sign-in.";
const RESULT_NOTE =
  "The user must change this password at the first sign-in before using the app.";

function stubCreate(body: Record<string, string>): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

async function createUser(password?: string): Promise<void> {
  const user = userEvent.setup();
  render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
  await user.type(screen.getByLabelText("Email"), "new@example.com");
  await user.type(screen.getByLabelText("Full name"), "New User");
  if (password) await user.type(screen.getByLabelText(/^Password/), password);
  await user.click(screen.getByRole("button", { name: "Create" }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("create-user must-change note", () => {
  // Scenario: The create-user form says the password must be changed at the first sign-in
  it("says it in the form, in English and Portuguese", () => {
    render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);

    expect(screen.getByText(FORM_NOTE)).toBeInTheDocument();
    expect(en.admin.createUserDescription).toBe(FORM_NOTE);
    expect(pt.admin.createUserDescription).toBe(
      "O novo usuário terá de trocar a senha no primeiro login.",
    );
    expect(pt.admin.createMustChangeNote).toBe(
      "O usuário terá de trocar esta senha no primeiro login antes de usar o app.",
    );
  });

  // Scenario: The result of a create with a generated password repeats the note
  it("repeats it next to the generated password", async () => {
    stubCreate({
      id: "u1",
      email: "new@example.com",
      temp_password: GENERATED_PASSWORD,
    });

    await createUser();

    const result = await screen.findByRole("status");
    expect(result).toHaveTextContent(
      `User created. Temporary password: ${GENERATED_PASSWORD}`,
    );
    expect(result).toHaveTextContent(RESULT_NOTE);
    expect(screen.queryByText(FORM_NOTE)).not.toBeInTheDocument();
  });

  // Scenario: The result of a create with a typed password repeats the note
  it("repeats it without echoing a typed password", async () => {
    stubCreate({ id: "u1", email: "new@example.com" });

    await createUser(TYPED_PASSWORD);

    const result = await screen.findByRole("status");
    expect(result).toHaveTextContent("User created successfully.");
    expect(result).toHaveTextContent(RESULT_NOTE);
    expect(document.body.textContent).not.toContain(TYPED_PASSWORD);
  });
});
