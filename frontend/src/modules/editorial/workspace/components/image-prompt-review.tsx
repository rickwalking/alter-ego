"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import type { ImagePromptReviewProps } from "./types";

export function ImagePromptReview({
  prompts,
  readOnly = true,
}: ImagePromptReviewProps): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review");

  if (!prompts?.length) {
    return null;
  }

  return (
    <section
      className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm"
      aria-label={t("imagePromptsTitle")}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">{t("imagePromptsTitle")}</p>
        <NeonBadge variant="secondary">
          {t("imagePromptsCount", { count: prompts.length })}
        </NeonBadge>
      </div>
      <div className="space-y-3">
        {prompts.map((prompt) => {
          const inputId = `image-prompt-${prompt.slide_index}`;
          const promptText =
            prompt.rendered_image_prompt?.trim() || prompt.image_prompt;
          const metadataBadges = [
            prompt.image_model ? `Model: ${prompt.image_model}` : null,
            prompt.image_style ? `Style: ${prompt.image_style}` : null,
            prompt.theme_name ? `Theme: ${prompt.theme_name}` : null,
            prompt.image_generation_key
              ? `Key: ${prompt.image_generation_key.slice(0, 10)}`
              : null,
          ].filter((value): value is string => value !== null);

          return (
            <article
              key={`${prompt.slide_index}-${prompt.title}`}
              className="space-y-2 rounded-md border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)] p-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <label className="font-medium" htmlFor={inputId}>
                  {t("imagePromptForSlide", { index: prompt.slide_index })}
                </label>
                <NeonBadge variant="outline">{prompt.title}</NeonBadge>
              </div>
              {metadataBadges.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {metadataBadges.map((badge) => (
                    <NeonBadge key={badge} variant="secondary">
                      {badge}
                    </NeonBadge>
                  ))}
                </div>
              )}
              <NeonTextarea
                id={inputId}
                aria-label={t("imagePromptTextareaLabel", {
                  index: prompt.slide_index,
                })}
                defaultValue={promptText}
                readOnly={readOnly}
                rows={prompt.rendered_image_prompt ? 7 : 4}
              />
            </article>
          );
        })}
      </div>
    </section>
  );
}
