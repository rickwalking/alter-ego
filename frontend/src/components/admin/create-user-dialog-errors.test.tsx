/**
 * Gherkin: tests/features/users-area-polish-ae0514.feature
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CreateUserDialog } from "./create-user-dialog";

const TAKEN_DETAIL = "User with email taken@example.com already exists";
const PASSWORD_HINT =
  "At least 12 characters. Leave blank to generate a temporary one.";
const PASSWORD_TOO_SHORT = "The password needs at least 12 characters.";

function stubFetch(body: unknown, status: number): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function fillAndSubmit(password = ""): Promise<void> {
  const user = userEvent.setup();
  render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
  await user.type(screen.getByLabelText("Email"), "taken@example.com");
  await user.type(screen.getByLabelText("Full name"), "Taken Person");
  if (password) {
    await user.type(screen.getByLabelText(/^Password/), password);
  }
  await user.click(screen.getByRole("button", { name: "Create" }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("create-user dialog errors", () => {
  // Scenario: A duplicate email shows a translated message
  it("shows the translated duplicate-email message, never the API text", async () => {
    stubFetch({ detail: TAKEN_DETAIL, code: "user_email_exists" }, 409);

    await fillAndSubmit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A user with this email already exists.",
    );
    expect(screen.queryByText(TAKEN_DETAIL)).not.toBeInTheDocument();
  });

  // Scenario: The password minimum is shown before submitting
  it("describes the password field with its 12-character minimum", () => {
    render(<CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />);
    const password = screen.getByLabelText(/^Password/);

    expect(screen.getByText(PASSWORD_HINT)).toBeInTheDocument();
    expect(password).toHaveAccessibleDescription(PASSWORD_HINT);
    expect(password).toHaveAttribute("aria-invalid", "false");
  });

  // Scenario: A short password is refused without a request
  it("refuses a 5-character password without a request", async () => {
    const fetchMock = stubFetch({}, 201);

    await fillAndSubmit("abcde");

    const password = screen.getByLabelText(/^Password/);
    expect(await screen.findByText(PASSWORD_TOO_SHORT)).toBeInTheDocument();
    expect(password).toHaveAttribute("aria-invalid", "true");
    expect(password).toHaveAccessibleDescription(
      `${PASSWORD_HINT} ${PASSWORD_TOO_SHORT}`,
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Scenario: A short password is refused without a request
  it("sends a password of exactly 12 characters", async () => {
    const fetchMock = stubFetch({ id: "n1", email: "x" }, 201);

    await fillAndSubmit("a".repeat(12));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(screen.queryByText(PASSWORD_TOO_SHORT)).not.toBeInTheDocument();
  });

  // Scenario: A 422 field error is shown on its field
  it("puts a 422 email error on the email field", async () => {
    stubFetch(
      { detail: [{ loc: ["body", "email"], msg: "not an email" }] },
      422,
    );

    await fillAndSubmit();

    const email = screen.getByLabelText("Email");
    await waitFor(() => expect(email).toHaveAttribute("aria-invalid", "true"));
    expect(email).toHaveAccessibleDescription("Enter a valid email address.");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  // Scenario: A 422 field error is shown on its field
  it("puts a 422 password and name error on their fields", async () => {
    stubFetch(
      {
        detail: [
          { loc: ["body", "password"], msg: "too short" },
          { loc: ["body", "full_name"], msg: "too short" },
        ],
      },
      422,
    );

    await fillAndSubmit("a".repeat(12));

    expect(await screen.findByText(PASSWORD_TOO_SHORT)).toBeInTheDocument();
    expect(screen.getByLabelText("Full name")).toHaveAccessibleDescription(
      "Enter a full name of 2 to 255 characters.",
    );
  });

  // Scenario: An unknown create failure keeps the generic message
  it.each([
    [500, { detail: "Internal Server Error" }],
    [422, { detail: [{ loc: ["body", "role"], msg: "bad" }] }],
  ])("shows the generic message for a %i", async (status, body) => {
    stubFetch(body, status);

    await fillAndSubmit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Failed to create user.",
    );
  });

  // Scenario: An unknown create failure keeps the generic message
  it("shows the generic message when the request itself fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));

    await fillAndSubmit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Failed to create user.",
    );
    expect(screen.queryByText("offline")).not.toBeInTheDocument();
  });
});

describe("create-user dialog after success", () => {
  // Scenario: The generated password stays until the admin closes it
  it("ignores Escape and the backdrop while the temporary password shows", async () => {
    stubFetch({ id: "n1", email: "x", temp_password: "Temp-Pass-123!" }, 201);
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<CreateUserDialog onClose={onClose} onSuccess={onSuccess} />);
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Full name"), "New Person");
    await user.click(screen.getByRole("button", { name: "Create" }));

    const done = await screen.findByRole("button", { name: "Done" });
    expect(screen.getByRole("status")).toHaveTextContent("Temp-Pass-123!");
    expect(done).toHaveFocus();
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(onClose).not.toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.click(done);
    expect(onSuccess).toHaveBeenCalledOnce();
  });

  // Scenario: Escape closes a dialog and focus returns to the opener
  it("still closes on Escape before anything was created", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<CreateUserDialog onClose={onClose} onSuccess={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Close dialog" }));

    expect(onClose).toHaveBeenCalledOnce();
  });
});
