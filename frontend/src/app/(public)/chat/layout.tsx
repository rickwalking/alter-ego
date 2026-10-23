import type { Viewport } from "next";
import { SkipLink } from "@/components/atoms/skip-link";
import { PublicHeader } from "@/components/layout/public-header";
import {
  PUBLIC_CHAT_SHELL_STYLE,
  PUBLIC_CHAT_VIEWPORT,
} from "./chat-shell-style";

export const viewport: Viewport = PUBLIC_CHAT_VIEWPORT;

/**
 * The site header (home link, nav, language switcher) above a chat that fills
 * the dynamic viewport, so the composer never hides under mobile browser bars;
 * the side insets keep both clear of a landscape notch.
 */
export default function PublicChatLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.ReactElement {
  return (
    <div
      className="flex h-dvh flex-col overflow-hidden"
      style={PUBLIC_CHAT_SHELL_STYLE}
    >
      <SkipLink />
      <PublicHeader />
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
