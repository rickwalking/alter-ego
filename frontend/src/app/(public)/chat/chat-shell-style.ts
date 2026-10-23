import type { Viewport } from "next";

/** Lets the composer use the safe-area insets (home indicator, notch). */
export const PUBLIC_CHAT_VIEWPORT: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

/** The page frame: above the grid background, clear of the notch and status bar. */
export const PUBLIC_CHAT_SHELL_STYLE: React.CSSProperties = {
  position: "relative",
  zIndex: 1,
  paddingTop: "env(safe-area-inset-top)",
  paddingLeft: "env(safe-area-inset-left)",
  paddingRight: "env(safe-area-inset-right)",
};
