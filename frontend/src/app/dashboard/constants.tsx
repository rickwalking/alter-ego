import React from "react";

/* ── SVG Icon Path Components ── */
/* Each returns only the <path>/<circle>/<rect> children,
   since the page.tsx wraps them in a consistent <svg> shell. */

function GridPaths() {
  return (
    <>
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
    </>
  );
}

function FileTextPaths() {
  return (
    <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
  );
}

function ClockPaths() {
  return (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </>
  );
}

function ShieldPaths() {
  return <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />;
}

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
  NEON_GLOW_CYAN_STAT,
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

/* ── Stat Card Configuration ── */

export interface StatCardConfig {
  label: string;
  value: string;
  change?: { value: string; trend: "up" | "down" };
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  valueColor: string;
  valueGlow: string;
}

export const STAT_CARDS: StatCardConfig[] = [
  {
    label: "Active Carousels",
    value: "24",
    change: { value: "+3 this week", trend: "up" },
    icon: <GridPaths />,
    iconBg: NEON_CYAN_DIM,
    iconColor: NEON_CYAN,
    valueColor: NEON_CYAN,
    valueGlow: NEON_GLOW_CYAN_STAT,
  },
  {
    label: "Published Posts",
    value: "87",
    change: { value: "+12 this month", trend: "up" },
    icon: <FileTextPaths />,
    iconBg: NEON_MAGENTA_DIM,
    iconColor: NEON_MAGENTA,
    valueColor: NEON_CYAN,
    valueGlow: NEON_GLOW_CYAN_STAT,
  },
  {
    label: "Processing",
    value: "6",
    change: { value: "-2", trend: "down" },
    icon: <ClockPaths />,
    iconBg: NEON_TEAL_DIM,
    iconColor: NEON_TEAL,
    valueColor: NEON_CYAN,
    valueGlow: NEON_GLOW_CYAN_STAT,
  },
  {
    label: "Scheduled",
    value: "11",
    change: { value: "+5", trend: "up" },
    icon: <ShieldPaths />,
    iconBg: NEON_AMBER_DIM,
    iconColor: NEON_AMBER,
    valueColor: NEON_CYAN,
    valueGlow: NEON_GLOW_CYAN_STAT,
  },
];

/* ── Quick Action Configuration ── */

export interface QuickActionConfig {
  title: string;
  description: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
}

export const QUICK_ACTIONS: QuickActionConfig[] = [
  {
    title: "New Carousel",
    description:
      "Start a new carousel project from scratch or from a template.",
    icon: <PlusPaths />,
    iconBg: NEON_CYAN_DIM,
    iconColor: NEON_CYAN,
  },
  {
    title: "Write Blog Post",
    description: "Draft a new blog article with AI-assisted editing.",
    icon: <EditPaths />,
    iconBg: NEON_MAGENTA_DIM,
    iconColor: NEON_MAGENTA,
  },
  {
    title: "Open Chat",
    description: "Ask the Alter Ego anything about projects and knowledge.",
    icon: <ChatPaths />,
    iconBg: NEON_AMBER_DIM,
    iconColor: NEON_AMBER,
  },
];

/* ── Activity Configuration ── */

export interface ActivityConfig {
  dotColor: string;
  title: string;
  description: string;
  time: string;
}

export const RECENT_ACTIVITIES: ActivityConfig[] = [
  {
    dotColor: NEON_GREEN,
    title: 'Carousel published: "DeepSeek V4 Analysis"',
    description:
      "Published to Instagram and LinkedIn. 2.4k impressions in first hour.",
    time: "12 minutes ago",
  },
  {
    dotColor: NEON_CYAN,
    title: "Blog post draft completed",
    description:
      '"Building RAG Pipelines with LangGraph" passed AI review. Ready for human review.',
    time: "1 hour ago",
  },
  {
    dotColor: NEON_AMBER,
    title: 'Workflow approved: "Cybersecurity Carousel"',
    description: "Phase 3 (Content) completed. Moving to image generation.",
    time: "3 hours ago",
  },
  {
    dotColor: NEON_MAGENTA,
    title: 'New persona created: "Tech Lead"',
    description: "Persona profile for senior engineering audience targeting.",
    time: "5 hours ago",
  },
  {
    dotColor: NEON_TEAL,
    title: "Scheduled publication confirmed",
    description:
      '"AI Competition Landscape" carousel set for May 28 at 10:00 AM.',
    time: "Yesterday at 4:15 PM",
  },
];

export const UPCOMING_SCHEDULE: ActivityConfig[] = [
  {
    dotColor: NEON_CYAN,
    title: '"Kubernetes Security Guide" carousel',
    description: "Scheduled for May 29 - Image generation pending",
    time: "Tomorrow, 10:00 AM",
  },
  {
    dotColor: NEON_TEAL,
    title: '"Event-Driven Architecture" blog post',
    description: "Draft approved. Scheduled for publishing.",
    time: "May 30, 2:00 PM",
  },
  {
    dotColor: NEON_MAGENTA,
    title: 'Persona review: "Engineering Manager"',
    description: "Awaiting approval before use in content pipeline.",
    time: "Jun 1, 11:00 AM",
  },
  {
    dotColor: NEON_AMBER,
    title: "Weekly content review meeting",
    description: "Review progress, approve pending items.",
    time: "Jun 3, 9:00 AM",
  },
];
