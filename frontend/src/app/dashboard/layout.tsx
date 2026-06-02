"use client";

import {
  NeonGridBackground,
  NeonScanlineOverlay,
} from "@/components/organisms";
import { NeonSidebar } from "@/components/organisms/neon-sidebar";
import {
  DASHBOARD_SIDEBAR_SECTIONS,
  SIDEBAR_WIDTH_PX,
} from "@/components/organisms/constants";
import { TEXT } from "@/constants/neon";

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.ReactElement {
  return (
    <>
      <NeonGridBackground />
      <NeonScanlineOverlay />

      <div
        className="min-h-full flex flex-col"
        style={{
          color: TEXT,
          fontFamily: "Inter, system-ui, sans-serif",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div className="flex min-h-screen">
          <NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} showUserFooter />

          <div
            className="flex flex-1 flex-col min-h-screen"
            style={{ marginLeft: `${SIDEBAR_WIDTH_PX}px` }}
          >
            <main
              className="flex-1"
              style={{ display: "flex", flexDirection: "column" }}
            >
              {children}
            </main>
          </div>
        </div>
      </div>
    </>
  );
}
