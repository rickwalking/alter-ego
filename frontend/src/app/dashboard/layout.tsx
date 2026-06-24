"use client";

import {
  NeonGridBackground,
  NeonScanlineOverlay,
} from "@/components/organisms";
import { NeonSidebar } from "@/components/organisms/neon-sidebar";
import { NeonIcon } from "@/components/atoms/neon-icon";
import { DASHBOARD_SIDEBAR_SECTIONS } from "@/components/organisms/constants";
import { BG_CARD, NEON_BORDER_SUBTLE, NEON_CYAN, TEXT } from "@/constants/neon";
import { useOffCanvas } from "@/lib/use-off-canvas";

const SIDEBAR_ID = "dashboard-sidebar";
const ICON_HAMBURGER = "M3 6h18M3 12h18M3 18h18";
const ICON_CLOSE = "M18 6 6 18M6 6l12 12";

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.ReactElement {
  const { open, toggle, close } = useOffCanvas();

  return (
    <>
      <NeonGridBackground />
      <NeonScanlineOverlay />

      {/* Mobile menu trigger — layout-level so the shared NeonTopBar stays
          presentational. Hidden once the persistent rail appears at lg. */}
      <button
        type="button"
        onClick={toggle}
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        aria-controls={SIDEBAR_ID}
        className="fixed left-2 top-2 z-50 flex h-11 w-11 items-center justify-center rounded-md lg:hidden"
        style={{
          background: BG_CARD,
          border: `1px solid ${NEON_BORDER_SUBTLE}`,
          color: NEON_CYAN,
        }}
      >
        <NeonIcon path={open ? ICON_CLOSE : ICON_HAMBURGER} />
      </button>

      {/* Backdrop — only below lg while the drawer is open. */}
      {open && (
        <button
          type="button"
          aria-label="Close menu"
          tabIndex={-1}
          onClick={close}
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
        />
      )}

      {/* Sidebar is a root-level sibling of the backdrop (NOT inside the z-1
          content context) so its z-40 actually sits ABOVE the z-30 backdrop —
          nesting it under a z-1 stacking context made the backdrop cover the
          drawer and its menu items. */}
      <NeonSidebar
        sections={DASHBOARD_SIDEBAR_SECTIONS}
        showUserFooter
        open={open}
        id={SIDEBAR_ID}
      />

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
          {/* min-w-0 is essential: as a flex item it defaults to min-width:auto
              and would grow to its widest child's min-content, making inner
              `overflow-x-auto` regions (progress steps, kanban, calendar) expand
              the page instead of scrolling. min-w-0 lets it shrink to the viewport. */}
          <div className="flex min-w-0 flex-1 flex-col min-h-screen lg:ml-[240px]">
            <main className="flex-1 flex flex-col">{children}</main>
          </div>
        </div>
      </div>
    </>
  );
}
