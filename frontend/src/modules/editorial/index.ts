/**
 * `editorial` — bounded-context public contract (AE-0138).
 *
 * Owns the carousel-authoring workspace + the editorial review workflow
 * (notifications, content calendar, kanban, collaborative editing) migrated
 * from the legacy `features/create` and `features/workflow` folders. This
 * barrel is the ONLY import surface for cross-context and `app/` consumers;
 * everything else under `modules/editorial/**` is internal.
 *
 * Subdivisions:
 *   - `workspace/` — carousel creation hooks, the editorial workflow driver,
 *     and the slide/presentation review utilities (was `features/create`).
 *   - `workflow/`  — review workflow surface: notifications, content calendar,
 *     kanban, collaborative edit/lock (was `features/workflow`).
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

/* --- workspace: types --- */
export type { CreateWorkflowControlsProps } from "./workspace/types";

/* --- workspace: editorial workflow / AI-assist types (canonical home; AE-0138) --- */
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
} from "./workspace/types-ai";

/* --- workspace: hooks --- */
export {
  useCreateCarousel,
  useCarouselProject,
  useDeleteCarousel,
  useAvailableStrategies,
  useRegenerateSlides,
} from "./workspace/hooks";
export {
  useEditorialWorkflow,
  type EditorialReviseOptions,
} from "./workspace/hooks/use-editorial-workflow";

/* --- workspace: components --- */
export {
  ImagePromptReview,
  type ImagePromptReviewProps,
} from "./workspace/components/image-prompt-review";
export {
  PresentationIconPreview,
  type PresentationIconPreviewProps,
} from "./workspace/components/presentation-icon-preview";
export {
  PresentationStructuredItems,
  type PresentationStructuredItemsProps,
} from "./workspace/components/presentation-structured-items";
export {
  WorkflowFailedCard,
  type WorkflowFailedCardProps,
} from "./workspace/components/workflow-failed-card";

/* --- workspace: presentation review utilities --- */
export {
  PRESENTATION_STRUCTURED_EXTRA_KEYS,
  PRESENTATION_STRUCTURED_ITEM_LIST_KEYS,
  asRecord,
  presentationHeading,
  presentationBody,
  resolveSlideDraftTitle,
  resolveSlideDraftPreview,
  resolveHeadingBudget,
  resolveBodyBudget,
  formatBudgetUsage,
  isBudgetExceeded,
  localizedSlidesHaveBudgetViolations,
  isPresentationStructuredItem,
  isPresentationStructuredItemList,
  listPresentationStructuredItems,
  resolvePresentationPreviewText,
  listStructuredExtras,
  collectIconNames,
  listPresentationIconNames,
  hasBlockingPresentationViolations,
  listPresentationViolations,
  applySlideCopyEdit,
  slidesHaveCopyChanges,
  resolveLocalizedSlides,
  type PresentationStructuredItem,
  type PresentationFieldBudget,
  type PresentationLocaleKey,
  type EditableCopyField,
  type SlideCopyEdit,
} from "./workspace/lib/presentation-review-utils";

/* --- workflow: types --- */
export type { ReviewAssignmentPayload, ContentLock } from "./workflow/types";

/* --- workflow: hooks --- */
export {
  useContentCalendar,
  type CalendarItem,
  type ContentCalendar,
} from "./workflow/hooks/use-content-calendar";
export {
  useWorkflowKanban,
  type KanbanCard,
  type KanbanColumn,
  type WorkflowKanban,
} from "./workflow/hooks/use-workflow-kanban";
export { useNotifications } from "./workflow/hooks/use-notifications";
export { useCollaborativeEdit } from "./workflow/hooks/use-collaborative-edit";

/* --- workflow: components --- */
export { NotificationCenter } from "./workflow/components/notification-center";
export { ReviewAssignmentPanel } from "./workflow/components/review-assignment-panel";
export { ScheduledPublishPicker } from "./workflow/components/scheduled-publish-picker";
export { VersionDiffView } from "./workflow/components/version-diff-view";
export { BlogPostEditExtras } from "./workflow/components/blog-post-edit-extras";

/* --- workflow: utils --- */
export { isLockedByAnotherUser } from "./workflow/utils/collaborative-lock";
