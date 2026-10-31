import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  USER_FILTER_ROLE_ADMIN,
  USER_FILTER_ROLE_ALL,
  USER_FILTER_STATUS_ALL,
  USER_FILTER_STATUS_INACTIVE,
} from "@/constants/admin-users";
import { UserFilterToolbar } from "./user-filter-toolbar";

function StatefulToolbar() {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState(USER_FILTER_ROLE_ALL);
  const [status, setStatus] = useState(USER_FILTER_STATUS_ALL);
  return (
    <UserFilterToolbar
      query={query}
      role={role}
      status={status}
      onQueryChange={setQuery}
      onRoleChange={setRole}
      onStatusChange={setStatus}
    />
  );
}

function renderToolbar(
  overrides: Partial<Parameters<typeof UserFilterToolbar>[0]> = {},
) {
  const props = {
    query: "",
    role: USER_FILTER_ROLE_ALL,
    status: USER_FILTER_STATUS_ALL,
    onQueryChange: vi.fn(),
    onRoleChange: vi.fn(),
    onStatusChange: vi.fn(),
    ...overrides,
  };
  render(<UserFilterToolbar {...props} />);
  return props;
}

describe("UserFilterToolbar", () => {
  /**
   * Scenario: Search and filter controls are keyboard accessible.
   */
  it("renders labelled search and filter controls", () => {
    renderToolbar();

    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveAttribute(
      "placeholder",
      "Search by name or email",
    );
    expect(screen.getByRole("combobox", { name: "Role" })).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: "Status" }),
    ).toBeInTheDocument();
  });

  /**
   * Scenario: Search and filter controls are keyboard accessible.
   */
  it("moves focus from search to role to status with Tab", async () => {
    const user = userEvent.setup();
    renderToolbar();

    await user.tab();
    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("combobox", { name: "Role" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("combobox", { name: "Status" })).toHaveFocus();
  });

  /**
   * Scenario: Search matches a name regardless of case and accents.
   */
  it("reports search text as the admin types", async () => {
    const user = userEvent.setup();
    render(<StatefulToolbar />);
    const searchbox = screen.getByRole("searchbox", { name: "Search" });

    await user.type(searchbox, "joao");

    expect(searchbox).toHaveValue("joao");
  });

  /**
   * Scenario: Role filter narrows the rows.
   */
  it("reports the picked role", async () => {
    const user = userEvent.setup();
    const props = renderToolbar();

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Role" }),
      USER_FILTER_ROLE_ADMIN,
    );

    expect(props.onRoleChange).toHaveBeenCalledWith(USER_FILTER_ROLE_ADMIN);
  });

  /**
   * Scenario: Status filter narrows the rows.
   */
  it("reports the picked status", async () => {
    const user = userEvent.setup();
    const props = renderToolbar();

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Status" }),
      USER_FILTER_STATUS_INACTIVE,
    );

    expect(props.onStatusChange).toHaveBeenCalledWith(
      USER_FILTER_STATUS_INACTIVE,
    );
  });
});
