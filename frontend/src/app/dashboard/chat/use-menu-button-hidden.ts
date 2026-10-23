"use client";

import { useEffect } from "react";
import { DASHBOARD_MENU_BUTTON_ATTRIBUTE } from "@/constants/a11y";
import { useMediaQuery } from "@/lib/use-media-query";

/** Below this width the conversations list is a drawer (the sidebar uses it too). */
export const CHAT_DRAWER_MEDIA_QUERY = "(max-width: 767px)";

const HIDDEN = "hidden";
const INERT = "inert";

/**
 * While the conversations drawer is open on a narrow screen, the dashboard's
 * menu button is hidden and inert: it sits in a higher stacking context than
 * the drawer, so z-index alone cannot put the drawer above it. On a wider
 * screen (a phone rotated to landscape) the list is no drawer, so the menu
 * button comes back even if the drawer state is still open.
 */
export function useMenuButtonHidden(drawerOpen: boolean): void {
  const isDrawer = useMediaQuery(CHAT_DRAWER_MEDIA_QUERY);
  const hidden = drawerOpen && isDrawer;
  useEffect(() => {
    if (!hidden) return;
    const button = document.querySelector<HTMLElement>(
      `[${DASHBOARD_MENU_BUTTON_ATTRIBUTE}]`,
    );
    if (!button) return;
    button.setAttribute(INERT, "");
    button.style.visibility = HIDDEN;
    return () => {
      button.removeAttribute(INERT);
      button.style.visibility = "";
    };
  }, [hidden]);
}
