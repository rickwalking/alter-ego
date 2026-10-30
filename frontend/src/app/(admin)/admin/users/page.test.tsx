import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  USER_FILTER_ROLE_ADMIN,
  USER_FILTER_ROLE_ALL,
  USER_FILTER_STATUS_ALL,
  USER_FILTER_STATUS_INACTIVE,
} from "@/constants/admin-users";
import UsersPage from "./page";

const USERS_PAYLOAD = {
  items: [
    {
      id: "1",
      email: "joao@example.com",
      full_name: "João Silva",
      role: "admin",
      is_active: true,
      created_at: "2026-10-01T00:00:00Z",
    },
    {
      id: "2",
      email: "ana@example.com",
      full_name: "Ana Souza",
      role: "editor",
      is_active: false,
      created_at: "2026-10-02T00:00:00Z",
    },
    {
      id: "3",
      email: "jose.lima@example.com",
      full_name: "José Lima",
      role: "editor",
      is_active: true,
      created_at: "2026-10-03T00:00:00Z",
    },
  ],
  total: 3,
};

function mockUsersFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(USERS_PAYLOAD), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

async function renderLoadedPage(): Promise<ReturnType<typeof userEvent.setup>> {
  mockUsersFetch();
  const user = userEvent.setup();
  render(<UsersPage />);
  await waitFor(() =>
    expect(screen.getByText("João Silva")).toBeInTheDocument(),
  );
  return user;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("UsersPage filtering", () => {
  /**
   * Scenario: Search matches a name regardless of case and accents.
   */
  it("filters rows by search term", async () => {
    const user = await renderLoadedPage();
    const searchbox = screen.getByRole("searchbox", { name: "Search" });

    await user.type(searchbox, "ana");

    expect(screen.queryByText("João Silva")).not.toBeInTheDocument();
    expect(screen.getByText("Ana Souza")).toBeInTheDocument();
  });

  /**
   * Scenario: No match shows a filter-specific empty message.
   */
  it("shows a filter-specific empty message when nothing matches", async () => {
    const user = await renderLoadedPage();
    const searchbox = screen.getByRole("searchbox", { name: "Search" });

    await user.type(searchbox, "zzz");

    expect(screen.getByText("No users match the filters.")).toBeInTheDocument();
    expect(screen.queryByText("Ana Souza")).not.toBeInTheDocument();
  });

  /**
   * Scenario: Role filter narrows the rows.
   */
  it("filters rows by role", async () => {
    const user = await renderLoadedPage();

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Role" }),
      USER_FILTER_ROLE_ADMIN,
    );

    expect(screen.getByText("João Silva")).toBeInTheDocument();
    expect(screen.queryByText("Ana Souza")).not.toBeInTheDocument();
  });

  /**
   * Scenario: Status filter narrows the rows.
   */
  it("filters rows by status", async () => {
    const user = await renderLoadedPage();

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Status" }),
      USER_FILTER_STATUS_INACTIVE,
    );

    expect(screen.getByText("Ana Souza")).toBeInTheDocument();
    expect(screen.queryByText("João Silva")).not.toBeInTheDocument();
  });

  /**
   * Scenario: Clearing the filters restores the full list.
   */
  it("restores the full list when filters are cleared", async () => {
    const user = await renderLoadedPage();
    const searchbox = screen.getByRole("searchbox", { name: "Search" });

    await user.type(searchbox, "ana");
    expect(screen.queryByText("João Silva")).not.toBeInTheDocument();

    await user.clear(searchbox);
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Role" }),
      USER_FILTER_ROLE_ALL,
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Status" }),
      USER_FILTER_STATUS_ALL,
    );

    expect(screen.getByText("João Silva")).toBeInTheDocument();
    expect(screen.getByText("José Lima")).toBeInTheDocument();
    expect(screen.getByText("Ana Souza")).toBeInTheDocument();
  });
});
