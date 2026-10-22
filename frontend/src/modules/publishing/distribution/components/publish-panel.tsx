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
import { InstagramTab, LinkedInTab } from "./publish-panel-tabs";
import { LanguageTabs } from "./publish-panel-parts";
import { LeaveGuardDialog } from "./leave-guard-dialog";
import type { PublishPanelProps } from "./types";
import { useCopyEditor } from "@/modules/publishing/distribution/hooks/use-copy-editor";
import { useLeaveGuard } from "@/modules/publishing/distribution/hooks/use-leave-guard";
import type { CopyField } from "@/modules/publishing/distribution/hooks/types";
import {
  viewerSlidePaths,
  viewerSlideTitle,
} from "@/modules/publishing/distribution/lib/viewer-slides";
import type {
  ViewerLanguage,
  ViewerSlideSource,
} from "@/modules/publishing/distribution/types";

type LanguageTab = ViewerLanguage;

const CAPTION_ONLY: readonly CopyField[] = ["caption"];
const LINKEDIN_POSTS: readonly CopyField[] = ["linkedinPt", "linkedinEn"];
const LINKEDIN_AND_CAPTION: readonly CopyField[] = [
  ...CAPTION_ONLY,
  ...LINKEDIN_POSTS,
];
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

export function PublishPanel({
  project,
  onPublishInstagram,
  isPublishingInstagram,
  publishResult,
  cacheBustToken,
  slideNumbers,
  onSaveCopy,
}: Readonly<PublishPanelProps>) {
  const t = useTranslations("publish");
  const [activeTab, setActiveTab] = useState<ActiveTab>("instagram");
  const [language, setLanguage] = useState<LanguageTab>("pt");
  const editor = useCopyEditor(project, onSaveCopy);
  const guard = useLeaveGuard(
    editor.canSave && editor.isDirty(LINKEDIN_AND_CAPTION),
  );

  const slideUrls = slideUrlsFromProject(
    { project, language, slideNumbers },
    cacheBustToken,
  );
  const activeLinkedInField: CopyField =
    language === "pt" ? "linkedinPt" : "linkedinEn";
  const saveBar = (fields: readonly CopyField[]) =>
    editor.canSave
      ? {
          dirty: editor.isDirty(fields),
          status: editor.status,
          onSave: () => editor.save(fields),
        }
      : undefined;

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
            caption={editor.draft.caption}
            onCaptionChange={(text) => editor.setText("caption", text)}
            save={saveBar(CAPTION_ONLY)}
            language={language}
            onPublishInstagram={onPublishInstagram}
            isPublishingInstagram={isPublishingInstagram}
            publishResult={publishResult}
          />
        )}
        {activeTab === "linkedin" && (
          <LinkedInTab
            text={editor.draft[activeLinkedInField]}
            onTextChange={(text) => editor.setText(activeLinkedInField, text)}
            save={saveBar(LINKEDIN_POSTS)}
            language={language}
            setLanguage={setLanguage}
            pdfHref={pdfUrl(project, language, cacheBustToken)}
          />
        )}
      </section>
      <LeaveGuardDialog guard={guard} />
    </div>
  );
}
