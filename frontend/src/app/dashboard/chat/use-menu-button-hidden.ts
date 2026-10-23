"use client";

import { useEffect } from "react";
import { DASHBOARD_MENU_BUTTON_ATTRIBUTE } from "@/constants/a11y";

const HIDDEN = "hidden";
const INERT = "inert";

/**
 * While ``hidden`` is true (the conversations drawer is open), the dashboard's
 * menu button is hidden and inert: it sits in a higher stacking context than
 * the drawer, so z-index alone cannot put the drawer above it.
 */
export function useMenuButtonHidden(hidden: boolean): void {
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
