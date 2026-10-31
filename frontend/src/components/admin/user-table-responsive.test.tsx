/**
 * Gherkin: tests/features/users-area-polish-ae0514.feature
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { USER_CARDS_MEDIA_QUERY } from "@/constants/admin-users";
import { BG_CARD } from "@/constants/neon";
import { BADGE_COLORS } from "@/schemas/neon-badge";
import {
  ADMIN_ROLE_BADGE_VARIANT,
  EDITOR_ROLE_BADGE_VARIANT,
  RoleBadge,
} from "./role-badge";
import { UserTable } from "./user-table";

const USERS = [
  {
    id: "u1",
    email: "a.very.long.address.for.a.phone@example.com",
    full_name: "Ana Souza",
    role: "editor",
    is_active: true,
    created_at: "2026-10-01T00:00:00Z",
  },
  {
    id: "u2",
    email: "admin@example.com",
    full_name: "João Silva",
    role: "admin",
    is_active: false,
    created_at: "2026-10-02T00:00:00Z",
  },
];
const AA_TEXT_CONTRAST = 4.5;

function phoneWidth(): void {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: query === USER_CARDS_MEDIA_QUERY,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

type Rgba = [number, number, number, number];

function parseColor(color: string): Rgba {
  if (color.startsWith("#")) {
    const hex = color.slice(1);
    return [0, 2, 4]
      .map((at) => Number.parseInt(hex.slice(at, at + 2), 16))
      .concat(1) as Rgba;
  }
  const parts = color
    .replace(/rgba?\(|\)/g, "")
    .split(",")
    .map(Number);
  return [parts[0] ?? 0, parts[1] ?? 0, parts[2] ?? 0, parts[3] ?? 1];
}

function over(top: Rgba, base: Rgba): Rgba {
  const alpha = top[3];
  const mix = (i: number): number => top[i]! * alpha + base[i]! * (1 - alpha);
  return [mix(0), mix(1), mix(2), 1];
}

function luminance([r, g, b]: Rgba): number {
  const channel = (value: number): number => {
    const c = value / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrast(text: string, background: string): number {
  const card = parseColor(BG_CARD);
  const bg = over(parseColor(background), card);
  const fg = over(parseColor(text), bg);
  const [light, dark] = [luminance(fg), luminance(bg)].sort((a, b) => b - a);
  return (light! + 0.05) / (dark! + 0.05);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("user list on a phone", () => {
  // Scenario: User rows stack as cards on a phone
  it("renders one card per user with every field and no table", () => {
    phoneWidth();
    render(<UserTable users={USERS} onRefresh={vi.fn()} />);

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    const cards = screen.getAllByRole("listitem");
    expect(cards).toHaveLength(2);
    const first = within(cards[0]!);
    expect(first.getByText("Ana Souza")).toBeInTheDocument();
    expect(first.getByText(USERS[0]!.email)).toHaveClass("break-all");
    expect(first.getByText("Editor")).toBeInTheDocument();
    expect(first.getByText("Active")).toBeInTheDocument();
    expect(first.getByText(/^Created:/)).toBeInTheDocument();
    expect(within(cards[1]!).getByText("Inactive")).toBeInTheDocument();
  });

  // Scenario: User rows stack as cards on a phone
  it("opens the dialog of the card's user", async () => {
    phoneWidth();
    const user = userEvent.setup();
    render(<UserTable users={USERS} onRefresh={vi.fn()} />);
    const second = within(screen.getAllByRole("listitem")[1]!);

    await user.click(second.getByRole("button", { name: "Delete" }));

    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "admin@example.com",
    );
  });

  // Scenario: Row actions are large enough to tap
  it("gives every row action and dialog button a 44 px minimum", async () => {
    phoneWidth();
    const user = userEvent.setup();
    render(<UserTable users={USERS} onRefresh={vi.fn()} />);
    const actions = within(screen.getAllByRole("listitem")[0]!).getAllByRole(
      "button",
    );
    expect(actions).toHaveLength(3);
    actions.forEach((button) => expect(button).toHaveClass("min-h-11"));

    await user.click(actions[0]!);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("button", { name: "Save" })).toHaveClass(
      "min-h-11",
    );
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveClass(
      "min-h-11",
    );
  });
});

describe("user list on a wide screen", () => {
  // Scenario: User rows stack as cards on a phone
  it("keeps the table inside its own horizontal scroll box", () => {
    render(<UserTable users={USERS} onRefresh={vi.fn()} />);
    const table = screen.getByRole("table");
    expect(table.parentElement).toHaveClass("overflow-x-auto");
    expect(screen.getAllByRole("row")).toHaveLength(3);
  });
});

describe("role badge", () => {
  // Scenario: The role badge is readable
  it.each([
    ["admin", "Admin"],
    ["editor", "Editor"],
  ])("shows the translated name for %s", (role, label) => {
    render(<RoleBadge role={role} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  // Scenario: The role badge is readable
  it.each([ADMIN_ROLE_BADGE_VARIANT, EDITOR_ROLE_BADGE_VARIANT])(
    "the %s badge text has at least 4.5:1 contrast on the card",
    (variant) => {
      const colors = BADGE_COLORS[variant];
      expect(contrast(colors.text, colors.bg)).toBeGreaterThanOrEqual(
        AA_TEXT_CONTRAST,
      );
    },
  );

  // Scenario: The role badge is readable
  it("the helper refuses a low-contrast pair, so the check can fail", () => {
    expect(contrast("#777777", "#ffffff")).toBeLessThan(AA_TEXT_CONTRAST);
    expect(contrast("#ffffff", "rgba(0,0,0,0)")).toBeGreaterThan(10);
  });
});
