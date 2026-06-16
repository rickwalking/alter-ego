"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { WorkflowFailedCard } from "@/modules/editorial";

const BACK_LINK_STYLE = {
  display: "inline-block",
  marginTop: "12px",
  fontSize: "13px",
  color: "#00d4ff",
  textDecoration: "none",
} as const;

export interface PublishFailedNoticeProps {
  currentPhase: string;
  errorMessage: string | null | undefined;
  workspaceHref: string;
}

/**
 * Failed-state notice for the publish page (AE-0009, AC#19).
 *
 * When the editorial workflow's ``phase_status`` is ``failed``, the publish
 * page renders this notice instead of the "awaiting final approval" message.
 * It surfaces the {@link WorkflowFailedCard} (error message + retry) plus a
 * "Back to workspace" link so the user can recover from the publish screen.
 */
export function PublishFailedNotice({
  currentPhase,
  errorMessage,
  workspaceHref,
}: PublishFailedNoticeProps): React.ReactElement {
  const t = useTranslations("publish");
  return (
    <div style={{ marginBottom: "16px" }}>
      <WorkflowFailedCard
        currentPhase={currentPhase}
        errorMessage={errorMessage}
        onRetry={() => {
          window.location.href = workspaceHref;
        }}
        isRetrying={false}
      />
      <Link href={workspaceHref} style={BACK_LINK_STYLE}>
        {t("backToWorkspace")}
      </Link>
    </div>
  );
}
