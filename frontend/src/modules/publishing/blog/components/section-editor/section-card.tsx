"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import {
  BLOG_EDITOR_I18N_NAMESPACE,
  BLOG_HEADING_MAX_LENGTH,
  BLOG_SECTION_MAX_LENGTH,
} from "@/constants/blog-editor";
import { NEON_RED } from "@/constants/neon";
import { BLOG_EDITOR_ERR_ALT_REQUIRED } from "../../editor-content";
import { EditorErrorNotice } from "../editor-error-notice";
import { ImageSlot } from "./image-slot";
import type { SectionCardProps } from "./types";

const LABEL_CLASS = "mb-1 block text-xs font-semibold text-text-muted";
const BODY_ROWS = 10;

type SectionToolbarProps = Pick<
  SectionCardProps,
  "index" | "count" | "readOnly" | "onMove" | "onDelete"
>;

/** Move up / move down / delete, disabled at the ends and for the last section. */
function SectionToolbar({
  index,
  count,
  readOnly,
  onMove,
  onDelete,
}: SectionToolbarProps): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  return (
    <div className="flex gap-1">
      <NeonButton
        size="sm"
        variant="ghost"
        disabled={readOnly || index === 0}
        onClick={() => onMove(-1)}
        aria-label={t("section.moveUp")}
      >
        {t("section.moveUp")}
      </NeonButton>
      <NeonButton
        size="sm"
        variant="ghost"
        disabled={readOnly || index === count - 1}
        onClick={() => onMove(1)}
        aria-label={t("section.moveDown")}
      >
        {t("section.moveDown")}
      </NeonButton>
      <NeonButton
        size="sm"
        variant="ghost"
        disabled={readOnly || count === 1}
        onClick={onDelete}
      >
        {t("section.delete")}
      </NeonButton>
    </div>
  );
}

/**
 * One section of the document (AE-0424): heading + markdown body, move
 * up/down, delete, its own image slot and "Rewrite this section in my voice".
 * The section keeps its stable id (and image) when it is reordered.
 */
export function SectionCard({
  section,
  index,
  count,
  language,
  readOnly,
  issue,
  imageStatus,
  rewriteStatus,
  onChange,
  onMove,
  onDelete,
  onGenerateImage,
  onRewrite,
  onSelectText,
}: Readonly<SectionCardProps>): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const prefix = `${language}-${section.id}`;
  const fieldIssue =
    issue && issue !== BLOG_EDITOR_ERR_ALT_REQUIRED ? issue : null;
  return (
    <NeonCard data-testid={`section-${section.id}`}>
      <NeonCardHeader className="flex flex-row items-center justify-between gap-2 pb-2">
        <NeonCardTitle className="text-base">
          {t("section.title", { number: index + 1 })}
        </NeonCardTitle>
        <SectionToolbar
          index={index}
          count={count}
          readOnly={readOnly}
          onMove={onMove}
          onDelete={onDelete}
        />
      </NeonCardHeader>
      <NeonCardContent className="space-y-3">
        <div>
          <label htmlFor={`${prefix}-heading`} className={LABEL_CLASS}>
            {t("section.heading")}
          </label>
          <NeonInput
            id={`${prefix}-heading`}
            value={section.heading ?? ""}
            maxLength={BLOG_HEADING_MAX_LENGTH}
            placeholder={t("section.headingPlaceholder")}
            disabled={readOnly}
            onChange={(e) => onChange({ heading: e.target.value })}
          />
        </div>
        <div>
          <label htmlFor={`${prefix}-body`} className={LABEL_CLASS}>
            {t("section.body")}
          </label>
          <NeonTextarea
            id={`${prefix}-body`}
            value={section.body_md}
            rows={BODY_ROWS}
            maxLength={BLOG_SECTION_MAX_LENGTH}
            className="font-mono"
            disabled={readOnly || rewriteStatus.pending}
            onChange={(e) => onChange({ body_md: e.target.value })}
            onSelect={(e) => {
              const { selectionStart, selectionEnd, value } = e.currentTarget;
              onSelectText(value.slice(selectionStart, selectionEnd));
            }}
          />
          {fieldIssue && (
            <p
              role="alert"
              className="mt-1 text-xs"
              style={{ color: NEON_RED }}
            >
              {t(`issues.${fieldIssue}`)}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <NeonButton
            size="sm"
            variant="secondary"
            disabled={readOnly || rewriteStatus.pending}
            loading={rewriteStatus.pending}
            onClick={onRewrite}
          >
            {t("section.rewrite")}
          </NeonButton>
        </div>
        {rewriteStatus.error && (
          <EditorErrorNotice error={rewriteStatus.error} />
        )}
        <ImageSlot
          slotId={`${prefix}-image`}
          label={t("section.image")}
          image={section.image}
          status={imageStatus}
          readOnly={readOnly}
          issue={issue === BLOG_EDITOR_ERR_ALT_REQUIRED ? issue : null}
          onGenerate={onGenerateImage}
          onChange={(image) => onChange({ image })}
        />
      </NeonCardContent>
    </NeonCard>
  );
}
