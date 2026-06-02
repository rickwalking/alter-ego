/** Dashboard App Router paths (neon shell). */
export const DASHBOARD_ROUTES = {
  HOME: "/dashboard",
  CHAT: "/dashboard/chat",
  CREATE: "/dashboard/create",
  CREATE_WORKSPACE: (id: string) => `/dashboard/create/${id}`,
  CREATE_PUBLISH: (id: string) => `/dashboard/create/${id}/publish`,
  BLOG_POSTS: "/dashboard/blog-posts",
  BLOG_POST_EDIT: (id: string) => `/dashboard/blog-posts/${id}/edit`,
  WORKFLOW: "/dashboard/workflow",
  CALENDAR: "/dashboard/calendar",
  RUBRICS: "/dashboard/rubrics",
  PERSONAS: "/dashboard/personas",
  KNOWLEDGE: "/dashboard/knowledge",
  ANALYTICS: "/dashboard/analytics",
} as const;
