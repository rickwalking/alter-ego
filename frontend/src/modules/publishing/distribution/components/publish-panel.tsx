"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { API_ENDPOINTS } from "@/constants/api";
import {
  appendCacheBuster,
  slideUrlsForPublishPanel,
} from "@/lib/carousel-media-url";
import { CaptionEditor, countHashtags } from "./caption-editor";
import { HorizontalCarouselViewer } from "./horizontal-carousel-viewer";
import type { EditorState, PublishPanelProps } from "./types";

const IG_MAX_CHARS = 2200;
const IG_MAX_HASHTAGS = 30;
const LINKEDIN_MAX_CHARS = 3000;
const LINKEDIN_COMPOSE_URL = "https://www.linkedin.com/feed/?shareActive=true";

type LanguageTab = "pt" | "en";
type ActiveTab = "instagram" | "linkedin";

// AE-0313: combine the project's updated_at with the freshly built artifact
// version (when a "Rebuild PDF" just ran) so served PDF/slide URLs are
// cache-busted on version change.
function cacheBustVersion(
  project: CarouselProjectResponse,
  cacheBustToken: string | undefined,
): string {
  return cacheBustToken
    ? `${project.updated_at}-${cacheBustToken}`
    : project.updated_at;
}

function slideUrlsFromProject(
  project: CarouselProjectResponse,
  language: "pt" | "en",
  cacheBustToken: string | undefined,
): string[] {
  const tokens = project.design_tokens as
    | {
        images?: {
          slides?: string[];
          rendered_slides_pt?: string[];
          rendered_slides_en?: string[];
        };
      }
    | null
    | undefined;
  // The publish viewer wants the RENDERED slides (with text overlay),
  // not the raw hero images. Fall back to legacy `slides` for projects
  // generated before the rendered_slides_* fields existed.
  const ptSlides =
    tokens?.images?.rendered_slides_pt ?? tokens?.images?.slides ?? [];
  const enSlides = tokens?.images?.rendered_slides_en ?? ptSlides;
  const slides = language === "en" ? enSlides : ptSlides;
  return slideUrlsForPublishPanel({
    projectId: project.id,
    paths: slides,
    language,
    updatedAt: cacheBustVersion(project, cacheBustToken),
  });
}

function pdfUrl(
  project: CarouselProjectResponse,
  language: "pt" | "en",
  cacheBustToken: string | undefined,
): string {
  return appendCacheBuster(
    `${API_ENDPOINTS.CAROUSEL_PDF(project.id)}?lang=${language}`,
    cacheBustVersion(project, cacheBustToken),
  );
}

function createEditorState(project: CarouselProjectResponse): EditorState {
  return {
    seed: JSON.stringify([
      project.caption ?? "",
      project.linkedin_post_pt ?? "",
      project.linkedin_post_en ?? "",
    ]),
    caption: project.caption ?? "",
    linkedinPt: project.linkedin_post_pt ?? "",
    linkedinEn: project.linkedin_post_en ?? "",
  };
}

export function PublishPanel({
  project,
  onPublishInstagram,
  isPublishingInstagram,
  publishResult,
  cacheBustToken,
}: PublishPanelProps) {
  const t = useTranslations("publish");
  const [activeTab, setActiveTab] = useState<ActiveTab>("instagram");
  const [language, setLanguage] = useState<LanguageTab>("pt");
  const incomingEditorState = createEditorState(project);
  const [editorState, setEditorState] = useState(incomingEditorState);
  const editor =
    editorState.seed === incomingEditorState.seed
      ? editorState
      : incomingEditorState;

  if (editorState.seed !== incomingEditorState.seed) {
    setEditorState(incomingEditorState);
  }

  const slideUrls = slideUrlsFromProject(project, language, cacheBustToken);
  const activeLinkedInText =
    language === "pt" ? editor.linkedinPt : editor.linkedinEn;
  const setCaption = (caption: string) =>
    setEditorState((state) => ({ ...state, seed: editor.seed, caption }));
  const setActiveLinkedInText = (text: string) =>
    setEditorState((state) => ({
      ...state,
      seed: editor.seed,
      ...(language === "pt" ? { linkedinPt: text } : { linkedinEn: text }),
    }));
  const hashtagCount = countHashtags(editor.caption);
  const hashtagsOver = hashtagCount > IG_MAX_HASHTAGS;

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard rejects in insecure contexts; caller should still succeed.
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1fr]">
      <section aria-label={t("carouselLabel")} className="space-y-3">
        <div
          role="tablist"
          aria-label={t("viewerLanguageLabel")}
          className="flex justify-end gap-1"
        >
          {(["pt", "en"] as LanguageTab[]).map((lang) => (
            <button
              key={lang}
              type="button"
              role="tab"
              aria-selected={language === lang}
              onClick={() => setLanguage(lang)}
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
        <HorizontalCarouselViewer
          slideUrls={slideUrls}
          alt={project.title || project.topic}
        />
        <a
          href={pdfUrl(project, language, cacheBustToken)}
          target="_blank"
          rel="noopener"
          className="inline-flex w-full items-center justify-center rounded-md border border-[var(--color-border)] px-4 py-2 font-medium text-sm hover:bg-[var(--color-background)]"
        >
          {t("downloadPdf")} ({language.toUpperCase()})
        </a>
      </section>

      <section className="space-y-4">
        <div
          role="tablist"
          aria-label={t("platformTabsLabel")}
          className="flex rounded-md border border-[var(--color-border)] p-1"
        >
          {(["instagram", "linkedin"] as ActiveTab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 rounded px-3 py-1.5 font-medium text-sm transition-colors ${
                activeTab === tab
                  ? "bg-[var(--color-primary)] text-[var(--color-text)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              {t(`tabs.${tab}`)}
            </button>
          ))}
        </div>

        {activeTab === "instagram" && (
          <div className="space-y-3">
            <CaptionEditor
              value={editor.caption}
              onChange={setCaption}
              maxChars={IG_MAX_CHARS}
              placeholder={t("instagram.placeholder")}
              ariaLabel={t("instagram.captionLabel")}
              helpText={t("instagram.hashtagHelp", {
                count: hashtagCount,
                max: IG_MAX_HASHTAGS,
              })}
            />
            {hashtagsOver && (
              <p className="text-destructive text-xs">
                {t("instagram.hashtagOver")}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => {
                  void copyToClipboard(editor.caption);
                }}
                className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-background)]"
              >
                {t("instagram.copyCaption")}
              </button>
              {onPublishInstagram && (
                <button
                  type="button"
                  onClick={() => {
                    void onPublishInstagram(editor.caption);
                  }}
                  disabled={
                    isPublishingInstagram ||
                    editor.caption.length === 0 ||
                    editor.caption.length > IG_MAX_CHARS ||
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
            {publishResult?.status === "success" && (
              <p className="text-success text-sm">{publishResult.message}</p>
            )}
            {publishResult?.status === "error" && (
              <p className="text-destructive text-sm">
                {publishResult.message}
              </p>
            )}
          </div>
        )}

        {activeTab === "linkedin" && (
          <div className="space-y-3">
            <div
              role="tablist"
              aria-label={t("linkedin.languageTabsLabel")}
              className="flex gap-1"
            >
              {(["pt", "en"] as LanguageTab[]).map((lang) => (
                <button
                  key={lang}
                  type="button"
                  role="tab"
                  aria-selected={language === lang}
                  onClick={() => setLanguage(lang)}
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
            <CaptionEditor
              value={activeLinkedInText}
              onChange={setActiveLinkedInText}
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
                  void copyToClipboard(activeLinkedInText);
                }}
                className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-background)]"
              >
                {t("linkedin.copyPost")}
              </button>
              <a
                href={pdfUrl(project, language, cacheBustToken)}
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
        )}
      </section>
    </div>
  );
}
