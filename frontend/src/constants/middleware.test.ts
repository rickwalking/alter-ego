import { describe, expect, it } from "vitest";
import {
  isDashboardRoute,
  isEditorDashboardRoute,
  isPublicRoute,
  isPublicChatRoute,
} from "@/constants/middleware";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";

describe("middleware route helpers", () => {
  describe("isPublicRoute", () => {
    it("Then home, blog, and public chat are public", () => {
      expect(isPublicRoute(PUBLIC_ROUTE_PATHS.HOME)).toBe(true);
      expect(isPublicRoute(PUBLIC_ROUTE_PATHS.BLOG)).toBe(true);
      expect(isPublicRoute(`${PUBLIC_ROUTE_PATHS.BLOG}/my-post`)).toBe(true);
      expect(isPublicRoute(PUBLIC_ROUTE_PATHS.CHAT)).toBe(true);
    });

    it("Then dashboard paths are not public", () => {
      expect(isPublicRoute(DASHBOARD_ROUTES.HOME)).toBe(false);
      expect(isPublicRoute(DASHBOARD_ROUTES.CREATE)).toBe(false);
    });
  });

  describe("isDashboardRoute", () => {
    it("Then dashboard prefix matches", () => {
      expect(isDashboardRoute(DASHBOARD_ROUTES.WORKFLOW)).toBe(true);
      expect(isDashboardRoute(PUBLIC_ROUTE_PATHS.CHAT)).toBe(false);
    });
  });

  describe("isEditorDashboardRoute", () => {
    it("Then chat and overview are not editor-only", () => {
      expect(isEditorDashboardRoute(DASHBOARD_ROUTES.CHAT)).toBe(false);
      expect(isEditorDashboardRoute(DASHBOARD_ROUTES.HOME)).toBe(false);
    });

    it("Then create and knowledge require editor", () => {
      expect(isEditorDashboardRoute(DASHBOARD_ROUTES.CREATE)).toBe(true);
      expect(isEditorDashboardRoute(DASHBOARD_ROUTES.KNOWLEDGE)).toBe(true);
    });
  });

  describe("isPublicChatRoute", () => {
    it("Then only /chat matches", () => {
      expect(isPublicChatRoute(PUBLIC_ROUTE_PATHS.CHAT)).toBe(true);
      expect(isPublicChatRoute(DASHBOARD_ROUTES.CHAT)).toBe(false);
    });
  });
});
