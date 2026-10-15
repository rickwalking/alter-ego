"use client";

import { useTranslations } from "next-intl";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import {
  BG_CARD,
  BG_DEEP,
  CYAN_GRADIENT,
  NEON_AMBER,
  NEON_AMBER_DIM,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import { CREATE_TEMPLATES } from "@/app/dashboard/create/constants";
import { canSubmitCreateForm } from "@/app/dashboard/create/helpers";
import {
  isPovForm,
  type CreateCarouselFormState,
} from "@/app/dashboard/create/types";
import { IMAGE_PRESETS, POV_TEMPLATES } from "@/constants/create";

const sidebarCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export interface CreateSidebarProps {
  form: CreateCarouselFormState;
  onSubmit: () => void;
  isPending: boolean;
  error: string | null;
}

function modeKey(form: CreateCarouselFormState): string {
  return isPovForm(form) ? "pov" : "radar";
}

function useTemplateName(form: CreateCarouselFormState): string {
  const t = useTranslations("create.pov.formats");
  if (!isPovForm(form)) {
    return CREATE_TEMPLATES[form.selectedTemplate]?.name ?? "—";
  }
  const pov = POV_TEMPLATES[form.selectedTemplate];
  return pov ? t(`${pov.format}.name`) : "—";
}

export function CreateSidebar({
  form,
  onSubmit,
  isPending,
  error,
}: CreateSidebarProps): React.ReactElement {
  const t = useTranslations("create");
  const templateName = useTemplateName(form);
  const preset = IMAGE_PRESETS.find((p) => p.value === form.imagePreset);

  const summaryRows = [
    { label: t("mode.summaryLabel"), value: t(`mode.${modeKey(form)}.name`) },
    { label: "Template", value: templateName },
    { label: "Theme", value: form.theme },
    {
      label: "Image preset",
      value: preset ? t(preset.labelKey) : form.imagePreset,
    },
    { label: "Topic", value: form.topic.trim() || "—" },
    { label: "Status", value: "Draft", badge: true },
  ] as const;

  return (
    <div
      style={{
        position: "sticky",
        top: "84px",
        alignSelf: "start",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <div style={sidebarCardStyle}>
        <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>
          Project Summary
        </h3>
        {summaryRows.map((row) => (
          <div
            key={row.label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "8px 0",
              fontSize: "13px",
              borderBottom: "1px solid rgba(255,255,255,0.03)",
              gap: "12px",
            }}
          >
            <span style={{ color: TEXT_DIM }}>{row.label}</span>
            {"badge" in row && row.badge ? (
              <span
                style={{
                  padding: "2px 6px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontWeight: 600,
                  background: NEON_AMBER_DIM,
                  color: NEON_AMBER,
                }}
              >
                {row.value}
              </span>
            ) : (
              <span
                style={{
                  color: TEXT,
                  fontWeight: 600,
                  textAlign: "right",
                  maxWidth: "60%",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {row.value}
              </span>
            )}
          </div>
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={onSubmit}
        disabled={isPending || !canSubmitCreateForm(form)}
        style={{
          width: "100%",
          padding: "12px",
          borderRadius: "6px",
          border: "none",
          background: CYAN_GRADIENT,
          color: BG_DEEP,
          fontSize: "13px",
          fontWeight: 700,
          cursor: isPending ? "wait" : "pointer",
          opacity: isPending ? 0.7 : 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          fontFamily: "inherit",
        }}
      >
        {isPending ? <NeonSpinner size="sm" /> : null}
        Start Carousel
      </button>
    </div>
  );
}
