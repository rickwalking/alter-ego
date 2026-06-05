"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import {
  BG_CARD,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import { CREATE_TEMPLATES } from "@/constants/create";
import {
  useAvailableStrategies,
  useRegenerateSlides,
} from "@/features/create/hooks";
import type { CarouselProjectResponse } from "@/schemas/carousel";

const CYAN = NEON_CYAN;
const CYAN_DIM = NEON_CYAN_DIM;

const sectionCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "24px",
};

export interface RegenerateStrategySectionProps {
  project: CarouselProjectResponse;
  projectId: string;
}

function findTemplateIndex(strategy: string | null | undefined): number {
  if (!strategy) return 0;
  return CREATE_TEMPLATES.findIndex((t) => t.strategy === strategy);
}

export function RegenerateStrategySection({
  project,
  projectId,
}: RegenerateStrategySectionProps): React.ReactElement {
  const t = useTranslations("publish.regenerateStrategy");
  const {
    data: strategiesData,
    isLoading,
    isError,
    refetch,
  } = useAvailableStrategies();
  const regenerate = useRegenerateSlides();
  const [selectedIndex, setSelectedIndex] = useState<number>(
    findTemplateIndex(project.slide_layout_strategy),
  );
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleTemplateSelect = useCallback(
    (idx: number) => {
      setSelectedIndex(idx);
      setSuccessMessage(null);
      regenerate.reset();
    },
    [regenerate],
  );

  const handleRegenerate = useCallback(() => {
    const template = CREATE_TEMPLATES[selectedIndex];
    if (!template) return;
    setSuccessMessage(null);
    regenerate.reset();
    regenerate.mutate(
      { projectId, strategy: template.strategy },
      { onSuccess: () => setSuccessMessage(t("success")) },
    );
  }, [selectedIndex, projectId, regenerate, t]);

  if (isLoading) {
    return (
      <div style={sectionCardStyle}>
        <div className="flex items-center gap-2">
          <NeonSpinner size="sm" />
          <span className="text-sm" style={{ color: TEXT_DIM }}>
            {t("loading")}
          </span>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div style={sectionCardStyle}>
        <p className="text-sm" style={{ color: TEXT_DIM }}>
          {t("fetchError")}
        </p>
        <NeonButton size="sm" variant="outline" onClick={() => void refetch()}>
          {t("retry")}
        </NeonButton>
      </div>
    );
  }

  return (
    <div style={sectionCardStyle}>
      <h3 className="text-sm font-semibold mb-1">{t("title")}</h3>
      <p className="text-xs mb-3" style={{ color: TEXT_DIM }}>
        {t("selectTemplate")}
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "10px",
          marginBottom: "16px",
        }}
      >
        {CREATE_TEMPLATES.map((tpl, idx) => {
          const isActive =
            idx === selectedIndex &&
            (strategiesData?.strategies.some((s) => s.name === tpl.strategy) ??
              false);
          return (
            <div
              key={tpl.name}
              role="button"
              tabIndex={0}
              onClick={() => handleTemplateSelect(idx)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  handleTemplateSelect(idx);
                }
              }}
              style={{
                background: isActive ? CYAN_DIM : BG_CARD,
                border: isActive
                  ? `1px solid ${CYAN}`
                  : "1px solid rgba(255,255,255,0.06)",
                borderRadius: "8px",
                padding: "14px",
                cursor: "pointer",
                transition: "all 0.2s",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "20px", marginBottom: "4px" }}>
                {tpl.icon}
              </div>
              <h4
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: TEXT,
                  margin: 0,
                }}
              >
                {tpl.name}
              </h4>
              <p
                style={{
                  fontSize: "10px",
                  color: TEXT_DIM,
                  margin: "4px 0 0",
                }}
              >
                {tpl.desc}
              </p>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-3">
        <NeonButton
          size="sm"
          disabled={regenerate.isPending}
          onClick={handleRegenerate}
        >
          {regenerate.isPending ? t("regenerating") : t("regenerate")}
        </NeonButton>
        {regenerate.isError && (
          <span className="text-xs text-red-400" role="alert">
            {regenerate.error instanceof Error
              ? regenerate.error.message
              : t("fetchError")}
          </span>
        )}
        {successMessage && (
          <span className="text-xs" style={{ color: NEON_CYAN }} role="status">
            {successMessage}
          </span>
        )}
      </div>
    </div>
  );
}
