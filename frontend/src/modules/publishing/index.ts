/**
 * `publishing` — bounded-context public contract (AE-0137).
 *
 * Owns the blog + distribution (Instagram/carousel publishing) + scheduling
 * surface migrated from the legacy `features/blog` and `features/publish`
 * folders. This barrel is the ONLY import surface for cross-context and `app/`
 * consumers; everything else under `modules/publishing/**` is internal.
 *
 * Hook disambiguation (glossary: the rejected name `CarouselArticle` is NOT
 * used; canonical = `BlogPost (origin = carousel)`):
 *   - `useCarouselBlogPosts` — carousel-origin blog posts (completed carousel
 *     projects rendered on the public `/blog` listing).
 *   - `useBlogPosts` — first-class blog posts (dashboard CRUD).
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

/* --- blog: types --- */
export type {
  BlogPost,
  BlogPostCreatePayload,
  BlogPostUpdatePayload,
} from "./blog/types";
export type {
  BlogAiSuggestResult,
  BlogAiImproveResult,
  BlogGenerateImageResult,
  VoiceScoreResult,
  RubricEvaluationResult,
  ContentSource,
  SlideValidationViolation,
  SlideValidationReport,
  LocalizedSlideReview,
  SlideImagePrompt,
  WorkflowPhaseStatus,
  EditorialWorkflowState,
} from "./blog/types-ai";

/* --- blog: hooks --- */
export {
  useBlogPosts,
  type BlogPostFilters,
} from "./blog/hooks/use-blog-posts";
export {
  useCarouselProject,
  useCarouselProjects,
  useCarouselBlogPosts,
  useCarouselBlog,
  useCarouselBlogWithDesign,
  useCarouselDesign,
  useCarouselSlides,
} from "./blog/hooks/use-carousel-blog";
export { useBlogAi } from "./blog/hooks/use-blog-ai";
export {
  useAccessibilityCheck,
  type AccessibilityIssue,
  type AccessibilityResult,
} from "./blog/hooks/use-accessibility-check";
export {
  useSeoAnalysis,
  type SeoAnalysisResult,
} from "./blog/hooks/use-seo-analysis";
export { useEditorShortcuts } from "./blog/hooks/use-editor-shortcuts";

/* --- blog: adapters --- */
export { mapProjectToBlogPostCard } from "./blog/adapters/blog-post-adapter";

/* --- blog: listing components --- */
export {
  NeonBlogPostCard,
  type NeonBlogPostCardComponentProps,
} from "./blog/components/listing/neon-blog-post-card";

/* --- blog: components --- */
export { AccessibilityChecker } from "./blog/components/accessibility-checker";
export { AiSuggestionPanel } from "./blog/components/ai-suggestion-panel";
export { BlogPostFilters as BlogPostFiltersPanel } from "./blog/components/blog-post-filters";
export { ImageGenModal } from "./blog/components/image-gen-modal";
export { KeyboardShortcutsHelp } from "./blog/components/keyboard-shortcuts-help";
export {
  RichTextEditor,
  type RichTextEditorProps,
} from "./blog/components/rich-text-editor";
export { SeoPreview } from "./blog/components/seo-preview";
export {
  VersionHistorySidebar,
  type BlogPostVersion,
} from "./blog/components/version-history-sidebar";

/* --- blog: public-post components --- */
export { BackLink } from "./blog/components/public-post/back-link";
export { BlogPostAdminPanel } from "./blog/components/public-post/blog-post-admin-panel";
export {
  BlogPostContent,
  extractH2Heading,
  resolveSlideImage,
} from "./blog/components/public-post/blog-post-content";
export { BlogPostHeader } from "./blog/components/public-post/blog-post-header";
export { BlogPostHero } from "./blog/components/public-post/blog-post-hero";

/* --- distribution: hooks --- */
export {
  usePublishInstagram,
  type InstagramPublishResponse,
} from "./distribution/hooks/use-publish";
export {
  usePublishChat,
  type UsePublishChatReturn,
} from "./distribution/hooks/use-publish-chat";

/* --- distribution: components --- */
export { PublishPanel } from "./distribution/components/publish-panel";
export { HorizontalCarouselViewer } from "./distribution/components/horizontal-carousel-viewer";
export {
  CaptionEditor,
  countHashtags,
} from "./distribution/components/caption-editor";
export { PublishFailedNotice } from "./distribution/components/publish-failed-notice";
export { RegenerateStrategySection } from "./distribution/components/regenerate-strategy-section";

/* --- distribution: lib / types --- */
export { mergePublishProjectWithWorkflow } from "./distribution/lib/merge-publish-project";
export type { RegenerateStrategySectionProps } from "./distribution/types";
