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
  ViolationSeverity,
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
export {
  useRepairCarousel,
  type RepairCarouselResponse,
  type RepairSlideDiff,
} from "./workspace/hooks/use-repair-carousel";

/* --- workspace: components --- */
export { AutoRepairButton } from "./workspace/components/auto-repair-button";
export { ImagePromptReview } from "./workspace/components/image-prompt-review";
export { PresentationIconPreview } from "./workspace/components/presentation-icon-preview";
export { PresentationStructuredItems } from "./workspace/components/presentation-structured-items";
export { WorkflowFailedCard } from "./workspace/components/workflow-failed-card";
export type {
  AutoRepairButtonProps,
  ImagePromptReviewProps,
  PresentationIconPreviewProps,
  PresentationStructuredItemsProps,
  WorkflowFailedCardProps,
} from "./workspace/components/types";

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
  hasBlockingContentGateValidation,
  listContentGateViolations,
  listContentReviewViolations,
  isWarningViolation,
  violationToneClasses,
  VIOLATION_SEVERITY_WARNING,
  VIOLATION_SEVERITY_BLOCKER,
  type PresentationStructuredItem,
  type PresentationFieldBudget,
} from "./workspace/lib/presentation-review-utils";

/* --- workspace: localized slide resolution + copy editing --- */
export {
  applySlideCopyEdit,
  slidesHaveCopyChanges,
  resolveLocalizedSlides,
  type PresentationLocaleKey,
  type EditableCopyField,
  type SlideCopyEdit,
} from "./workspace/lib/presentation-slide-resolution";

/* --- workflow: types --- */
export type { ReviewAssignmentPayload, ContentLock } from "./workflow/types";

/* --- workflow: hooks --- */
export { useContentCalendar } from "./workflow/hooks/use-content-calendar";
export { useWorkflowKanban } from "./workflow/hooks/use-workflow-kanban";
export type {
  CalendarItem,
  ContentCalendar,
  KanbanCard,
  KanbanColumn,
  WorkflowKanban,
} from "./workflow/hooks/types";
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
