"use client";

import { useTranslations } from "next-intl";
import { CaptionEditor, countHashtags } from "./caption-editor";
import { CopySaveBar } from "./copy-save-bar";
import { CopyVersionList } from "./copy-version-list";
import {
  CopyTextButton,
  LanguageTabs,
  PublishResultLine,
} from "./publish-panel-parts";
import type { InstagramTabProps, LinkedInTabProps } from "./types";
import {
  IG_MAX_CHARS,
  IG_MAX_HASHTAGS,
  LINKEDIN_MAX_CHARS,
  captionInvalid,
  linkedinInvalid,
} from "@/modules/publishing/distribution/lib/copy-limits";
import { DISTRIBUTION_FIELDS } from "@/modules/publishing/distribution/lib/copy-editor-state";

const LINKEDIN_COMPOSE_URL = "https://www.linkedin.com/feed/?shareActive=true";
const CAPTION_FIELDS: readonly string[] = [DISTRIBUTION_FIELDS.CAPTION];
const LINKEDIN_FIELDS: readonly string[] = [
  DISTRIBUTION_FIELDS.LINKEDIN_PT,
  DISTRIBUTION_FIELDS.LINKEDIN_EN,
];

/**
 * Caption editor, copy and (when wired) publish-now for Instagram.
 *
 * The Instagram caption is Portuguese only (the account posts in PT; no EN
 * caption is generated), so the EN viewer tab says so instead of presenting the
 * PT caption as English.
 */
export function InstagramTab({
  caption,
  onCaptionChange,
  language,
  onPublishInstagram,
  isPublishingInstagram,
  publishResult,
  save,
  history,
}: Readonly<InstagramTabProps>): React.ReactElement {
  const t = useTranslations("publish");
  const hashtagCount = countHashtags(caption);
  const hashtagsOver = hashtagCount > IG_MAX_HASHTAGS;
  const unsaved = save?.dirty === true;
  const publishBlocked =
    isPublishingInstagram === true ||
    unsaved ||
    caption.length === 0 ||
    captionInvalid(caption);
  return (
    <div className="space-y-3">
      {language === "en" && (
        <p
          role="note"
          className="rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-[var(--color-text-muted)] text-xs"
        >
          {t("instagram.captionPtOnly")}
        </p>
      )}
      <CaptionEditor
        value={caption}
        onChange={onCaptionChange}
        maxChars={IG_MAX_CHARS}
        placeholder={t("instagram.placeholder")}
        ariaLabel={t("instagram.captionLabel")}
        helpText={t("instagram.hashtagHelp", {
          count: hashtagCount,
          max: IG_MAX_HASHTAGS,
        })}
      />
      {hashtagsOver && (
        <p className="text-destructive text-xs">{t("instagram.hashtagOver")}</p>
      )}
      {save && <CopySaveBar {...save} invalid={captionInvalid(caption)} />}
      <div className="flex flex-wrap gap-2">
        <CopyTextButton
          text={caption}
          label={t("instagram.copyCaption")}
          disabled={unsaved}
        />
        {onPublishInstagram && (
          <button
            type="button"
            onClick={() => {
              void onPublishInstagram(caption);
            }}
            disabled={publishBlocked}
            className="rounded-md bg-[var(--color-primary)] px-4 py-1.5 font-medium text-sm text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPublishingInstagram
              ? t("instagram.publishing")
              : t("instagram.publishNow")}
          </button>
        )}
      </div>
      <PublishResultLine result={publishResult} />
      <CopyVersionList
        history={history}
        fields={CAPTION_FIELDS}
        blocked={unsaved}
      />
    </div>
  );
}

/** LinkedIn post editor (per language), copy, PDF and the compose link. */
export function LinkedInTab({
  text,
  onTextChange,
  language,
  setLanguage,
  pdfHref,
  save,
  history,
}: Readonly<LinkedInTabProps>): React.ReactElement {
  const t = useTranslations("publish");
  return (
    <div className="space-y-3">
      <LanguageTabs
        language={language}
        onChange={setLanguage}
        ariaLabel={t("linkedin.languageTabsLabel")}
        className="flex gap-1"
      />
      <CaptionEditor
        value={text}
        onChange={onTextChange}
        maxChars={LINKEDIN_MAX_CHARS}
        placeholder={t("linkedin.placeholder")}
        ariaLabel={t("linkedin.postLabel", {
          language: language.toUpperCase(),
        })}
        helpText={t("linkedin.help")}
      />
      {save && <CopySaveBar {...save} invalid={linkedinInvalid(text)} />}
      <div className="flex flex-wrap gap-2">
        <CopyTextButton
          text={text}
          label={t("linkedin.copyPost")}
          disabled={save?.dirty === true}
        />
        <a
          href={pdfHref}
          target="_blank"
          rel="noopener"
          className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-background)]"
        >
          {t("linkedin.downloadPdf")}
        </a>
        <a
          href={LINKEDIN_COMPOSE_URL}
          target="_blank"
          rel="noopener"
          className="rounded-md bg-[var(--color-primary)] px-4 py-1.5 font-medium text-sm text-[var(--color-text)]"
        >
          {t("linkedin.openLinkedIn")}
        </a>
      </div>
      <p className="rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-[var(--color-text-muted)] text-xs">
        {t("linkedin.manualSteps")}
      </p>
      <CopyVersionList
        history={history}
        fields={LINKEDIN_FIELDS}
        blocked={save?.dirty === true}
      />
    </div>
  );
}
