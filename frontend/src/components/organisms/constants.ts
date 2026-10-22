import type { SidebarSection } from "@/schemas/neon-sidebar";

export const DASHBOARD_SIDEBAR_SECTIONS: SidebarSection[] = [
  {
    sectionKey: "sectionMain",
    items: [
      {
        href: "/dashboard",
        labelKey: "dashboard",
        icon: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
      },
      {
        href: "/dashboard/chat",
        labelKey: "chat",
        icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
      },
    ],
  },
  {
    sectionKey: "sectionContent",
    items: [
      {
        href: "/dashboard/create",
        labelKey: "createCarousel",
        icon: "M12 5v14M5 12h14",
      },
      {
        href: "/dashboard/blog-posts",
        labelKey: "blogPosts",
        icon: "M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20",
      },
      {
        href: "/dashboard/workflow",
        labelKey: "workflowBoard",
        icon: "M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z",
      },
    ],
  },
  {
    sectionKey: "sectionManagement",
    items: [
      {
        href: "/dashboard/calendar",
        labelKey: "calendar",
        icon: "M3 4h18v18H3zM16 2v4M8 2v4M3 10h18",
      },
      {
        href: "/dashboard/rubrics",
        labelKey: "rubrics",
        icon: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 15l2 2 4-4",
      },
      {
        href: "/dashboard/personas",
        labelKey: "personas",
        icon: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
      },
      {
        href: "/dashboard/palettes",
        labelKey: "palettes",
        icon: "M12 22a10 10 0 1 1 10-10c0 2.8-2.2 4-4 4h-2a2 2 0 0 0-1 3.7A2 2 0 0 1 12 22zM7.5 10.5h.01M12 7.5h.01M16.5 10.5h.01",
      },
      {
        href: "/dashboard/knowledge",
        labelKey: "knowledge",
        icon: "M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2zM22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z",
      },
      {
        href: "/dashboard/analytics",
        labelKey: "analytics",
        icon: "M3 3v18h18M7 16l4-4 4 4 5-6",
      },
    ],
  },
  {
    sectionKey: "sectionAdmin",
    items: [
      {
        href: "/admin/users",
        labelKey: "adminUsers",
        icon: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
        access: "admin",
      },
    ],
  },
];

export const SIDEBAR_WIDTH_PX = 240;
/** Footer avatar dimensions (square) for the sidebar user block. */
export const SIDEBAR_AVATAR_SIZE = 28;
