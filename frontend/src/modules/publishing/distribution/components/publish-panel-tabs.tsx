"use client";

import { useTranslations } from "next-intl";
import { CaptionEditor, countHashtags } from "./caption-editor";
import type {
  InstagramTabProps,
  LanguageTabsProps,
  LinkedInTabProps,
  PublishPanelProps,
} from "./types";
import type { ViewerLanguage } from "@/modules/publishing/distribution/types";

const IG_MAX_CHARS = 2200;
const IG_MAX_HASHTAGS = 30;
const LINKEDIN_MAX_CHARS = 3000;
const LINKEDIN_COMPOSE_URL = "https://www.linkedin.com/feed/?shareActive=true";
const VIEWER_LANGUAGES: readonly ViewerLanguage[] = ["pt", "en"];

/**
 * The clipboard rejects in insecure contexts; the rejection is swallowed so the
 * caller still succeeds.
 */
async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {}
}

/** PT / EN switch (the viewer and the LinkedIn post share the language). */
export function LanguageTabs({
  language,
  onChange,
  ariaLabel,
  className,
}: Readonly<LanguageTabsProps>): React.ReactElement {
  return (
    <div role="tablist" aria-label={ariaLabel} className={className}>
      {VIEWER_LANGUAGES.map((lang) => (
        <button
          key={lang}
          type="button"
          role="tab"
          aria-selected={language === lang}
          onClick={() => onChange(lang)}
          className={`rounded-md border px-3 py-1 text-xs uppercase ${
            language === lang
              ? "border-[var(--color-primary)] text-[var(--color-primary)]"
              : "border-[var(--color-border)] text-[var(--color-text-muted)]"
          }`}
        >
          {lang}
        </button>
      ))}
    </div>
  );
}

function PublishResultLine({
  result,
}: Readonly<{
  result: PublishPanelProps["publishResult"];
}>): React.ReactElement | null {
  if (result?.status === "success") {
    return <p className="text-success text-sm">{result.message}</p>;
  }
  if (result?.status === "error") {
    return <p className="text-destructive text-sm">{result.message}</p>;
  }
  return null;
}

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
}: Readonly<InstagramTabProps>): React.ReactElement {
  const t = useTranslations("publish");
  const hashtagCount = countHashtags(caption);
  const hashtagsOver = hashtagCount > IG_MAX_HASHTAGS;
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
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            void copyToClipboard(caption);
          }}
          className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-background)]"
        >
          {t("instagram.copyCaption")}
        </button>
        {onPublishInstagram && (
          <button
            type="button"
            onClick={() => {
              void onPublishInstagram(caption);
            }}
            disabled={
              isPublishingInstagram === true ||
              caption.length === 0 ||
              caption.length > IG_MAX_CHARS ||
              hashtagsOver
            }
            className="rounded-md bg-[var(--color-primary)] px-4 py-1.5 font-medium text-sm text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPublishingInstagram
              ? t("instagram.publishing")
              : t("instagram.publishNow")}
          </button>
        )}
      </div>
      <PublishResultLine result={publishResult} />
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
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            void copyToClipboard(text);
          }}
          className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-background)]"
        >
          {t("linkedin.copyPost")}
        </button>
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
    </div>
  );
}
