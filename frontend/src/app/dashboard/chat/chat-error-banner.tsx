"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import {
  CHAT_ERROR_KIND,
  CHAT_MESSAGE_MAX_LENGTH,
} from "@/modules/conversation";
import type { ChatErrorBannerProps } from "./types";

const NO_RETRY: ReadonlySet<string> = new Set([
  CHAT_ERROR_KIND.TOO_LONG,
  CHAT_ERROR_KIND.NOT_FOUND,
  CHAT_ERROR_KIND.SESSION_EXPIRED,
]);

/**
 * The failed turn, in plain localized words, with the one action that helps:
 * Retry, or Sign in when the session expired. Technical detail stays in logs.
 * (A dashboard 404 also re-checks the session: an expired one redirects to the
 * login page, see the dashboard chat view.)
 */
export function ChatErrorBanner({
  kind,
  loginRedirect,
  onRetry,
  onNewChat,
}: Readonly<ChatErrorBannerProps>): React.ReactElement {
  const t = useTranslations("chat.errors");
  const loginHref = loginRedirect
    ? `${PUBLIC_ROUTE_PATHS.LOGIN}?redirect=${encodeURIComponent(loginRedirect)}`
    : PUBLIC_ROUTE_PATHS.LOGIN;
  return (
    <div
      role="alert"
      className="flex shrink-0 flex-wrap items-center gap-3 px-6 py-2 text-sm text-red-400"
    >
      <span>{t(kind, { max: CHAT_MESSAGE_MAX_LENGTH })}</span>
      {kind === CHAT_ERROR_KIND.SESSION_EXPIRED && (
        <Link href={loginHref} className="underline">
          {t("signIn")}
        </Link>
      )}
      {kind === CHAT_ERROR_KIND.NOT_FOUND && onNewChat && (
        <button type="button" onClick={onNewChat} className="underline">
          {t("newChat")}
        </button>
      )}
      {!NO_RETRY.has(kind) && (
        <button type="button" onClick={onRetry} className="underline">
          {t("retry")}
        </button>
      )}
    </div>
  );
}
