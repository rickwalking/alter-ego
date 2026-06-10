"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import {
  BG_CARD,
  NEON_RED,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";

const cardStyle = {
  background: BG_CARD,
  border: `1px solid ${NEON_RED}44`,
  borderRadius: "8px",
  padding: "24px",
};

const headerStyle = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  marginBottom: "12px",
};

const dotStyle = {
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  background: NEON_RED,
  flexShrink: 0 as const,
};

export interface WorkflowFailedCardProps {
  currentPhase: string;
  errorMessage: string | null | undefined;
  onRetry: () => void;
  isRetrying: boolean;
}

const PHASE_LABEL_KEY: Record<string, string> = {
  research: "sendBack.phases.research",
  outline: "sendBack.phases.outline",
  content: "sendBack.phases.content",
  design: "sendBack.phases.design",
  images: "sendBack.phases.images",
  final_review: "review.finalReview.title",
};

export function WorkflowFailedCard({
  currentPhase,
  errorMessage,
  onRetry,
  isRetrying,
}: WorkflowFailedCardProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow");

  const phaseLabelKey = PHASE_LABEL_KEY[currentPhase];
  const phaseLabel = phaseLabelKey ? t(phaseLabelKey) : currentPhase;

  return (
    <div style={cardStyle} role="alert">
      <div style={headerStyle}>
        <div style={dotStyle} />
        <span style={{ color: NEON_RED, fontWeight: 700, fontSize: "15px" }}>
          {t("failed.genericLabel")}
        </span>
      </div>
      <p style={{ color: TEXT, fontSize: "13px", margin: "0 0 4px 0" }}>
        {t("failed.phaseLabel", { phase: phaseLabel })}
      </p>
      <p style={{ color: TEXT_DIM, fontSize: "13px", margin: "0 0 4px 0" }}>
        {t("failed.description", { phase: phaseLabel })}
      </p>
      {errorMessage ? (
        <>
          <p
            style={{
              color: TEXT_DIM,
              fontSize: "12px",
              margin: "12px 0 4px 0",
              fontWeight: 600,
            }}
          >
            {t("failed.errorDetail")}
          </p>
          <pre
            style={{
              color: TEXT_DIM,
              fontSize: "12px",
              margin: "0 0 16px 0",
              padding: "8px 12px",
              background: "rgba(255,255,255,0.03)",
              borderRadius: "4px",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {errorMessage}
          </pre>
        </>
      ) : null}
      <NeonButton
        size="sm"
        disabled={isRetrying}
        onClick={onRetry}
      >
        {isRetrying ? (
          <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
            <NeonSpinner />
            {t("failed.retrying")}
          </span>
        ) : (
          t("failed.retryButton")
        )}
      </NeonButton>
    </div>
  );
}
