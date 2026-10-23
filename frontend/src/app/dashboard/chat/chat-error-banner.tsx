"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import {
  CHAT_ERROR_KIND,
  CHAT_MESSAGE_MAX_LENGTH,
} from "@/modules/conversation";
import type { ChatErrorBannerProps } from "./types";

/**
 * The failed turn, in plain localized words, with the actions that can help:
 * Try again only when nothing was saved yet (``canRetry``), Sign in when the
 * session expired, and Start a new chat whenever the view offers one (the way
 * out of a full or gone conversation). Technical detail stays in logs.
 */
export function ChatErrorBanner({
  kind,
  loginRedirect,
  canRetry = false,
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
      {canRetry && (
        <button type="button" onClick={onRetry} className="underline">
          {t("retry")}
        </button>
      )}
      {onNewChat && (
        <button type="button" onClick={onNewChat} className="underline">
          {t("newChat")}
        </button>
      )}
    </div>
  );
}
