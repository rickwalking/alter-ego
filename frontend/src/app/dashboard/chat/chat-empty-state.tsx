"use client";

import { useTranslations } from "next-intl";
import {
  DASHBOARD_CHAT_BORDER_LIGHT,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_CYAN_DIM,
  DASHBOARD_CHAT_TEXT,
  DASHBOARD_CHAT_TEXT_MUTED,
} from "@/modules/editorial-operations";

/** Translation keys of the suggested first questions, in display order. */
export const CHAT_SUGGESTION_KEYS = ["s1", "s2", "s3", "s4"] as const;

/**
 * First screen of a new chat: who the Alter-Ego is, and a few questions that
 * start a conversation in one tap (sent in the visitor's language).
 */
export function ChatEmptyState({
  onSuggestion,
}: Readonly<{ onSuggestion: (text: string) => void }>): React.ReactElement {
  const t = useTranslations("chat.empty");
  return (
    <section
      aria-labelledby="chat-empty-title"
      className="chat-empty mx-auto flex w-full max-w-xl flex-col gap-5 py-6 sm:py-10"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm"
          style={{
            background: DASHBOARD_CHAT_CYAN_DIM,
            color: DASHBOARD_CHAT_CYAN,
          }}
        >
          ◆
        </span>
        <div className="min-w-0">
          <h2
            id="chat-empty-title"
            className="text-lg font-semibold"
            style={{ color: DASHBOARD_CHAT_TEXT, textWrap: "balance" }}
          >
            {t("title")}
          </h2>
          <p
            className="mt-1 text-sm leading-relaxed"
            style={{ color: DASHBOARD_CHAT_TEXT_MUTED, textWrap: "pretty" }}
          >
            {t("intro")}
          </p>
        </div>
      </div>
      <div>
        <p
          id="chat-suggestions-label"
          className="mb-2 text-xs font-medium"
          style={{ color: DASHBOARD_CHAT_TEXT_MUTED }}
        >
          {t("suggestionsLabel")}
        </p>
        <ul
          aria-labelledby="chat-suggestions-label"
          className="flex flex-col gap-2"
        >
          {CHAT_SUGGESTION_KEYS.map((key) => (
            <li key={key}>
              <button
                type="button"
                onClick={() => onSuggestion(t(key))}
                className="group flex min-h-11 w-full items-center justify-between gap-3 rounded-lg px-4 py-2 text-left text-sm transition-colors duration-150 ease-out hover:bg-neon-cyan/8 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan motion-reduce:transition-none"
                style={{
                  border: `1px solid ${DASHBOARD_CHAT_BORDER_LIGHT}`,
                  color: DASHBOARD_CHAT_TEXT,
                  overflowWrap: "break-word",
                }}
              >
                <span className="min-w-0">{t(key)}</span>
                <span
                  aria-hidden="true"
                  className="shrink-0 transition-transform duration-150 ease-out group-hover:translate-x-0.5 motion-reduce:transition-none"
                  style={{ color: DASHBOARD_CHAT_CYAN }}
                >
                  →
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
