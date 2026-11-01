import { describe, expect, it, vi } from "vitest";

const locale = vi.hoisted(() => ({ value: "en" }));
vi.mock("next-intl/server", async () => {
  const en = (await import("@/i18n/locales/en.json")).default;
  const pt = (await import("@/i18n/locales/pt.json")).default;
  return {
    getTranslations: (namespace: string) => {
      const titles: Record<string, string> = (locale.value === "pt" ? pt : en)
        .pageTitles;
      return Promise.resolve((key: string) =>
        namespace === "pageTitles" ? (titles[key] ?? key) : key,
      );
    },
  };
});

import { generateMetadata as calendarMetadata } from "@/app/dashboard/calendar/layout";
import { generateMetadata as rubricsMetadata } from "@/app/dashboard/rubrics/layout";
import { generateMetadata as palettesMetadata } from "@/app/dashboard/palettes/layout";
import { generateMetadata as personasMetadata } from "@/app/dashboard/personas/layout";
import { generateMetadata as knowledgeMetadata } from "@/app/dashboard/knowledge/layout";
import { generateMetadata as workflowMetadata } from "@/app/dashboard/workflow/layout";
import { generateMetadata as blogPostsMetadata } from "@/app/dashboard/blog-posts/layout";
import { generateMetadata as analyticsMetadata } from "@/app/dashboard/analytics/layout";
import { generateMetadata as createMetadata } from "@/app/dashboard/create/layout";
import { generateMetadata as dashboardMetadata } from "@/app/dashboard/page";
import { generateMetadata as usersMetadata } from "@/app/(admin)/admin/users/layout";
import { generateMetadata as changePasswordMetadata } from "@/app/dashboard/account/password/layout";
import { generateMetadata as loginMetadata } from "@/app/login/layout";
import { generateMetadata as forbiddenMetadata } from "@/app/403/layout";
import { generateMetadata as notFoundMetadata } from "@/app/not-found";
import { generateMetadata as blogMetadata } from "@/app/(public)/blog/page";

describe("page titles", () => {
  // Scenario: Dashboard pages have their own titles
  it.each([
    [dashboardMetadata, "Dashboard · Pedro Marins"],
    [calendarMetadata, "Calendar · Pedro Marins"],
    [rubricsMetadata, "Rubrics · Pedro Marins"],
    [palettesMetadata, "Palettes · Pedro Marins"],
    [personasMetadata, "Personas · Pedro Marins"],
    [knowledgeMetadata, "Knowledge Base · Pedro Marins"],
    [workflowMetadata, "Workflow Board · Pedro Marins"],
    [blogPostsMetadata, "Blog Posts · Pedro Marins"],
    [analyticsMetadata, "Analytics · Pedro Marins"],
    [createMetadata, "Create Carousel · Pedro Marins"],
    [usersMetadata, "Users · Pedro Marins"],
    [changePasswordMetadata, "Change password · Pedro Marins"],
  ])("titles a dashboard page %#", async (generate, title) => {
    locale.value = "en";
    expect((await generate()).title).toBe(title);
  });

  // Scenario: Public pages have their own titles
  it.each([
    [blogMetadata, "Blog · Pedro Marins"],
    [loginMetadata, "Sign in · Pedro Marins"],
    [forbiddenMetadata, "Access denied · Pedro Marins"],
    [notFoundMetadata, "Page not found · Pedro Marins"],
  ])("titles a public page %#", async (generate, title) => {
    locale.value = "en";
    expect((await generate()).title).toBe(title);
  });

  // Scenario: The change-password page has its own title
  it.each([
    ["en", "Change password · Pedro Marins"],
    ["pt", "Alterar senha · Pedro Marins"],
  ])("titles the change-password page in %s", async (language, title) => {
    locale.value = language;
    expect((await changePasswordMetadata()).title).toBe(title);
  });
});
