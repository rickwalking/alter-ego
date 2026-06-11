"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import {
  FAILED_CARD_STYLE,
  FAILED_CARD_HEADER_STYLE,
  FAILED_CARD_DOT_STYLE,
  FAILED_CARD_PHASE_LABEL_KEY,
  FAILED_CARD_COLORS,
} from "@/features/create/constants";
import type { WorkflowFailedCardProps } from "@/features/create/types";

const { NEON_RED, TEXT, TEXT_DIM } = FAILED_CARD_COLORS;

export function WorkflowFailedCard({
  currentPhase,
  errorMessage,
  onRetry,
  isRetrying,
}: WorkflowFailedCardProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow");

  const phaseLabelKey = FAILED_CARD_PHASE_LABEL_KEY[currentPhase];
  const phaseLabel = phaseLabelKey ? t(phaseLabelKey) : currentPhase;

  return (
    <div style={FAILED_CARD_STYLE} role="alert">
      <div style={FAILED_CARD_HEADER_STYLE}>
        <div style={FAILED_CARD_DOT_STYLE} />
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
      <NeonButton size="sm" disabled={isRetrying} onClick={onRetry}>
        {isRetrying ? (
          <span
            style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
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
