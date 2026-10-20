/**
 * `publishing` — bounded-context public contract (AE-0137).
 *
 * Owns the blog + distribution (Instagram/carousel publishing) + scheduling
 * surface migrated from the legacy `features/blog` and `features/publish`
 * folders. This barrel is the ONLY import surface for cross-context and `app/`
 * consumers; everything else under `modules/publishing/**` is internal.
 *
 * Glossary: the rejected name `CarouselArticle` is NOT used; canonical =
 * `BlogPost (origin = carousel)`. The v1 carousel-blog hooks were deleted in
 * AE-0428 (the public `/blog` listing reads the public API directly).
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
  BlogPostMutationErrorCode,
  BlogPostOrigin,
  BlogPostStatus,
} from "./blog/constants";
export {
  BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED,
  BLOG_POST_ERR_SLUG_CONFLICT,
  BLOG_POST_ERR_VALIDATION,
  BLOG_POST_ERR_VERSION_CONFLICT,
  BLOG_POST_ORIGIN_CAROUSEL,
  BLOG_POST_ORIGIN_STANDALONE,
  BLOG_POST_ORIGINS,
  BLOG_POST_STATUSES,
  BlogPostMutationError,
  toBlogPostOrigin,
  toBlogPostStatus,
} from "./blog/constants";
export type {
  BlogAiSuggestResult,
  BlogAiImproveResult,
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
export { useBlogPosts } from "./blog/hooks/use-blog-posts";
export { useBlogPostEditor } from "./blog/hooks/use-blog-post-editor";
export type {
  BlogEditorData,
  BlogPostFilters,
  BlogReviewActions,
  UseBlogPostEditorResult,
} from "./blog/hooks/types";
export { useBlogEditorActions } from "./blog/hooks/use-blog-editor-actions";
export { useBlogEditorData } from "./blog/hooks/use-blog-editor-data";
export { useBlogReviewActions } from "./blog/hooks/use-blog-review-actions";
export { useUnsavedChangesGuard } from "./blog/hooks/use-unsaved-changes-guard";
export { activeDocument, applySuggestion } from "./blog/lib/editor-document";
export {
  BLOG_EXCERPT_MAX_LENGTH,
  BLOG_TITLE_MAX_LENGTH,
} from "./blog/editor-content";
export type {
  BlogEditorFieldError,
  BlogEditorValidation,
} from "./blog/editor-content";
export { useBlogAi } from "./blog/hooks/use-blog-ai";

/* --- blog: generation (AE-0425) --- */
export { BlogGenerationStatus } from "./blog/generation/blog-generation-status";
export { CreateBlogFromCarousel } from "./blog/generation/create-blog-from-carousel";
export { generateStandaloneBlogPost } from "./blog/generation/generation-requests";
export { isGenerationInProgress } from "./blog/generation/generation-state";
export {
  GENERATION_TOPIC_MAX_CHARS,
  GENERATION_TOPIC_MIN_CHARS,
} from "./blog/generation/generation-constants";

/* --- blog: listing components --- */
export { NeonBlogPostCard } from "./blog/components/listing/neon-blog-post-card";
export type { NeonBlogPostCardComponentProps } from "./blog/components/listing/types";

/* --- blog: components --- */
export { AiSuggestionPanel } from "./blog/components/ai-suggestion-panel";
export { EditorErrorNotice } from "./blog/components/editor-error-notice";
export {
  snapshotText,
  VersionHistorySidebar,
} from "./blog/components/version-history-sidebar";
/* --- blog: section editor (AE-0424) --- */
export { BlogSectionEditor } from "./blog/components/section-editor/blog-section-editor";
export { MigrationBanner } from "./blog/components/section-editor/migration-banner";
export { ReviewBar } from "./blog/components/section-editor/review-bar";
export { VoiceScore } from "./blog/components/section-editor/voice-score";
export type { SectionSelection } from "./blog/components/section-editor/types";
export type { BlogPostVersion } from "./blog/components/types";

/* --- blog: public-post components --- */
export { BackLink } from "./blog/components/public-post/back-link";
export { BlogLanguageSwitch } from "./blog/components/public-post/blog-language-switch";
export { BlogPostContent } from "./blog/components/public-post/blog-post-content";
export { BlogPostHeader } from "./blog/components/public-post/blog-post-header";
export { BlogPostHero } from "./blog/components/public-post/blog-post-hero";
export { PublicCoverImage } from "./blog/components/public-post/public-cover-image";

/* --- distribution: hooks --- */
export {
  usePublishInstagram,
  type InstagramPublishResponse,
} from "./distribution/hooks/use-publish";
export { usePublishChat } from "./distribution/hooks/use-publish-chat";
export type { UsePublishChatReturn } from "./distribution/hooks/types";
export {
  useRepublishCarousel,
  type RepublishCarouselResponse,
} from "./distribution/hooks/use-republish-carousel";
export {
  useEditCarouselSlides,
  type EditCarouselSlidesResponse,
} from "./distribution/hooks/use-edit-carousel-slides";

/* --- distribution: components --- */
export { PublishPanel } from "./distribution/components/publish-panel";
export { HorizontalCarouselViewer } from "./distribution/components/horizontal-carousel-viewer";
export {
  CaptionEditor,
  countHashtags,
} from "./distribution/components/caption-editor";
export { PublishFailedNotice } from "./distribution/components/publish-failed-notice";
export { RegenerateStrategySection } from "./distribution/components/regenerate-strategy-section";
export { RebuildPdfSection } from "./distribution/components/rebuild-pdf-section";
export { SlideTextEditSection } from "./distribution/components/slide-text-edit-section";

/* --- distribution: lib / types --- */
export { mergePublishProjectWithWorkflow } from "./distribution/lib/merge-publish-project";
export type { RegenerateStrategySectionProps } from "./distribution/types";
