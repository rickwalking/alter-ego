import React from "react";

function PlusPaths() {
  return (
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>
  );
}

function EditPaths() {
  return (
    <>
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </>
  );
}

function ChatPaths() {
  return (
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  );
}

import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";

import {
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_MAGENTA,
  NEON_MAGENTA_DIM,
  NEON_TEAL,
  NEON_TEAL_DIM,
  NEON_AMBER,
  NEON_AMBER_DIM,
  NEON_GREEN,
  NEON_RED,
} from "@/constants/neon";

export {
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_MAGENTA,
  NEON_MAGENTA_DIM,
  NEON_TEAL,
  NEON_TEAL_DIM,
  NEON_AMBER,
  NEON_AMBER_DIM,
  NEON_GREEN,
  NEON_RED,
};

/** Message key under `dashboard.overview.quickActions` (title + description). */
export type QuickActionKey = "newCarousel" | "writeBlogPost" | "openChat";

export interface QuickActionConfig {
  key: QuickActionKey;
  href: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
}

/**
 * Icons are path-only fragments (`<path>`/`<circle>`/`<rect>` children): the
 * dashboard page wraps them in a consistent `<svg>` shell.
 */
export const QUICK_ACTIONS: QuickActionConfig[] = [
  {
    key: "newCarousel",
    href: DASHBOARD_ROUTES.CREATE,
    icon: <PlusPaths />,
    iconBg: NEON_CYAN_DIM,
    iconColor: NEON_CYAN,
  },
  {
    key: "writeBlogPost",
    href: DASHBOARD_ROUTES.BLOG_POSTS,
    icon: <EditPaths />,
    iconBg: NEON_MAGENTA_DIM,
    iconColor: NEON_MAGENTA,
  },
  {
    key: "openChat",
    href: DASHBOARD_ROUTES.CHAT,
    icon: <ChatPaths />,
    iconBg: NEON_AMBER_DIM,
    iconColor: NEON_AMBER,
  },
];
