import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditUserDialog } from "./edit-user-dialog";
import { UserTable } from "./user-table";

const USER = {
  id: "u1",
  email: "fixed@example.com",
  full_name: "Jon Smith",
  role: "editor",
  is_active: true,
  created_at: "2026-10-01T00:00:00Z",
};
const NAME_INVALID = "Enter a full name of 1 to 255 characters.";

function stubFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function sentBody(
  fetchMock: ReturnType<typeof vi.fn>,
): Record<string, unknown> {
  const init = (fetchMock.mock.calls[0] as [string, RequestInit])[1];
  return JSON.parse(init.body as string) as Record<string, unknown>;
}

function renderDialog(onSuccess = vi.fn(), onClose = vi.fn()) {
  render(
    <EditUserDialog user={USER} onClose={onClose} onSuccess={onSuccess} />,
  );
  return screen.getByLabelText("Full name");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("edit-user name field", () => {
  // Scenario: Admin renames a user
  it("shows the current name and sends the trimmed new one", async () => {
    const fetchMock = stubFetch(jsonResponse(USER, 200));
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();
    const input = renderDialog(onSuccess, onClose);
    expect(input).toHaveValue("Jon Smith");

    await user.clear(input);
    await user.type(input, "  John Smith  ");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledOnce());
    expect(onClose).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/users/u1");
    expect(sentBody(fetchMock)).toEqual({
      role: "editor",
      is_active: true,
      full_name: "John Smith",
    });
  });

  // Scenario: A blank name is rejected before submit
  it("rejects a blank name without sending a request", async () => {
    const fetchMock = stubFetch(jsonResponse(USER, 200));
    const user = userEvent.setup();
    const input = renderDialog();

    await user.clear(input);
    await user.type(input, "   ");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText(NAME_INVALID)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Scenario: A name longer than 255 characters is rejected before submit
  it("rejects a 256-character name without sending a request", async () => {
    const fetchMock = stubFetch(jsonResponse(USER, 200));
    const user = userEvent.setup();
    const input = renderDialog();

    await user.clear(input);
    await user.click(input);
    await user.paste("a".repeat(256));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText(NAME_INVALID)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Scenario: The backend rejects the name
  it("maps a 422 validation list to the name message", async () => {
    stubFetch(jsonResponse({ detail: [{ msg: "too short" }] }, 422));
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    const input = renderDialog(onSuccess);

    await user.type(input, "!");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText(NAME_INVALID)).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  // Scenario: The backend rejects the name
  it("shows the API message for other failures", async () => {
    stubFetch(jsonResponse({ detail: "Cannot demote the last admin" }, 409));
    const user = userEvent.setup();
    renderDialog();

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(
      await screen.findByText("Cannot demote the last admin"),
    ).toBeInTheDocument();
  });

  // Scenario: The backend rejects the name
  it("falls back to the generic error when the failure has no message", async () => {
    stubFetch(new Response("bad gateway", { status: 502 }));
    const user = userEvent.setup();
    renderDialog();

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(
      await screen.findByText("Failed to update user."),
    ).toBeInTheDocument();
  });

  // Scenario: An unchanged name is not sent
  it("leaves full_name out when only the role changed", async () => {
    const fetchMock = stubFetch(jsonResponse(USER, 200));
    const user = userEvent.setup();
    renderDialog();

    await user.selectOptions(screen.getByLabelText("Role"), "admin");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(sentBody(fetchMock)).toEqual({ role: "admin", is_active: true });
  });

  // Scenario: The email is not editable
  it("shows the email as text with no email field", () => {
    renderDialog();

    expect(screen.getByText("fixed@example.com").tagName).toBe("P");
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
  });

  // Scenario: The field keeps a visible keyboard focus style
  it("keeps a focus-visible ring on the name input", () => {
    const input = renderDialog();

    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveClass("focus-visible:ring-2");
    expect(input).toHaveClass("focus:ring-primary-500");
  });
});

describe("users table after a rename", () => {
  // Scenario: Admin renames a user
  it("refreshes the table, which then shows the new name", async () => {
    stubFetch(jsonResponse({ ...USER, full_name: "John Smith" }, 200));
    const onRefresh = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <UserTable users={[USER]} onRefresh={onRefresh} />,
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const input = screen.getByLabelText("Full name");
    await user.clear(input);
    await user.type(input, "John Smith");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onRefresh).toHaveBeenCalledOnce());
    rerender(
      <UserTable
        users={[{ ...USER, full_name: "John Smith" }]}
        onRefresh={onRefresh}
      />,
    );
    expect(screen.getByText("John Smith")).toBeInTheDocument();
    expect(screen.queryByText("Jon Smith")).not.toBeInTheDocument();
  });
});
