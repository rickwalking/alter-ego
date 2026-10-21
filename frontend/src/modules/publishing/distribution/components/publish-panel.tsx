"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { API_ENDPOINTS } from "@/constants/api";
import {
  appendCacheBuster,
  slideUrlsForPublishPanel,
} from "@/lib/carousel-media-url";
import { HorizontalCarouselViewer } from "./horizontal-carousel-viewer";
import { InstagramTab, LanguageTabs, LinkedInTab } from "./publish-panel-tabs";
import type { EditorState, PublishPanelProps } from "./types";
import {
  viewerSlidePaths,
  viewerSlideTitle,
} from "@/modules/publishing/distribution/lib/viewer-slides";
import type {
  ViewerLanguage,
  ViewerSlideSource,
} from "@/modules/publishing/distribution/types";

type LanguageTab = ViewerLanguage;
type ActiveTab = "instagram" | "linkedin";

/**
 * Combines the project's updated_at with the freshly built artifact version
 * (when a Rebuild PDF just ran) so served PDF/slide URLs are cache-busted on
 * version change.
 */
function cacheBustVersion(
  project: CarouselProjectResponse,
  cacheBustToken: string | undefined,
): string {
  return cacheBustToken
    ? `${project.updated_at}-${cacheBustToken}`
    : project.updated_at;
}

function slideUrlsFromProject(
  source: ViewerSlideSource,
  cacheBustToken: string | undefined,
): string[] {
  return slideUrlsForPublishPanel({
    projectId: source.project.id,
    paths: viewerSlidePaths(source),
    language: source.language,
    updatedAt: cacheBustVersion(source.project, cacheBustToken),
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
  slideNumbers,
}: Readonly<PublishPanelProps>) {
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

  const slideUrls = slideUrlsFromProject(
    { project, language, slideNumbers },
    cacheBustToken,
  );
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

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1fr]">
      <section aria-label={t("carouselLabel")} className="space-y-3">
        <LanguageTabs
          language={language}
          onChange={setLanguage}
          ariaLabel={t("viewerLanguageLabel")}
          className="flex justify-end gap-1"
        />
        <HorizontalCarouselViewer
          slideUrls={slideUrls}
          alt={viewerSlideTitle(project, language)}
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
          <InstagramTab
            caption={editor.caption}
            onCaptionChange={setCaption}
            language={language}
            onPublishInstagram={onPublishInstagram}
            isPublishingInstagram={isPublishingInstagram}
            publishResult={publishResult}
          />
        )}
        {activeTab === "linkedin" && (
          <LinkedInTab
            text={activeLinkedInText}
            onTextChange={setActiveLinkedInText}
            language={language}
            setLanguage={setLanguage}
            pdfHref={pdfUrl(project, language, cacheBustToken)}
          />
        )}
      </section>
    </div>
  );
}
