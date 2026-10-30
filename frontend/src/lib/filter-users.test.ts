import { describe, expect, it } from "vitest";

import {
  USER_FILTER_ROLE_ADMIN,
  USER_FILTER_ROLE_ALL,
  USER_FILTER_ROLE_EDITOR,
  USER_FILTER_STATUS_ACTIVE,
  USER_FILTER_STATUS_ALL,
  USER_FILTER_STATUS_INACTIVE,
} from "@/constants/admin-users";
import { filterUsers, normalizeSearchText } from "@/lib/filter-users";

const USERS = [
  {
    full_name: "João Silva",
    email: "joao@example.com",
    role: "admin",
    is_active: true,
  },
  {
    full_name: "Ana Souza",
    email: "ana@example.com",
    role: "editor",
    is_active: false,
  },
  {
    full_name: "José Lima",
    email: "jose.lima@example.com",
    role: "editor",
    is_active: true,
  },
];

const ALL_FILTER = {
  query: "",
  role: USER_FILTER_ROLE_ALL,
  status: USER_FILTER_STATUS_ALL,
};

describe("normalizeSearchText", () => {
  it("strips accents and lowercases", () => {
    expect(normalizeSearchText("João SILVA")).toBe("joao silva");
    expect(normalizeSearchText("José")).toBe("jose");
  });
});

describe("filterUsers", () => {
  /**
   * Scenario: Search matches a name regardless of case and accents.
   */
  it("matches names case- and accent-insensitively", () => {
    const result = filterUsers(USERS, { ...ALL_FILTER, query: "joao" });
    expect(result.map((user) => user.full_name)).toEqual(["João Silva"]);
  });

  /**
   * Scenario: Search matches an email.
   */
  it("matches emails", () => {
    const result = filterUsers(USERS, { ...ALL_FILTER, query: "ANA@EXAMPLE" });
    expect(result.map((user) => user.email)).toEqual(["ana@example.com"]);
  });

  it("returns every user when the query is empty or whitespace", () => {
    expect(filterUsers(USERS, { ...ALL_FILTER, query: "   " })).toHaveLength(3);
  });

  it("returns no users when nothing matches", () => {
    expect(filterUsers(USERS, { ...ALL_FILTER, query: "zzz" })).toHaveLength(0);
  });

  /**
   * Scenario: Role filter narrows the rows.
   */
  it("filters by role", () => {
    const admins = filterUsers(USERS, {
      ...ALL_FILTER,
      role: USER_FILTER_ROLE_ADMIN,
    });
    expect(admins.map((user) => user.full_name)).toEqual(["João Silva"]);

    const editors = filterUsers(USERS, {
      ...ALL_FILTER,
      role: USER_FILTER_ROLE_EDITOR,
    });
    expect(editors).toHaveLength(2);
  });

  /**
   * Scenario: Status filter narrows the rows.
   */
  it("filters by status", () => {
    const active = filterUsers(USERS, {
      ...ALL_FILTER,
      status: USER_FILTER_STATUS_ACTIVE,
    });
    expect(active.map((user) => user.full_name)).toEqual([
      "João Silva",
      "José Lima",
    ]);

    const inactive = filterUsers(USERS, {
      ...ALL_FILTER,
      status: USER_FILTER_STATUS_INACTIVE,
    });
    expect(inactive.map((user) => user.full_name)).toEqual(["Ana Souza"]);
  });

  /**
   * Scenario: Combined filters must all match.
   */
  it("requires every active filter to match", () => {
    const result = filterUsers(USERS, {
      query: "lima",
      role: USER_FILTER_ROLE_EDITOR,
      status: USER_FILTER_STATUS_ACTIVE,
    });
    expect(result.map((user) => user.full_name)).toEqual(["José Lima"]);

    const noMatch = filterUsers(USERS, {
      query: "lima",
      role: USER_FILTER_ROLE_EDITOR,
      status: USER_FILTER_STATUS_INACTIVE,
    });
    expect(noMatch).toHaveLength(0);
  });

  /**
   * Scenario: Clearing the filters restores the full list.
   */
  it("returns the full list with all filters at their default", () => {
    expect(filterUsers(USERS, ALL_FILTER)).toHaveLength(3);
  });
});
