/**
 * Re-export shim (AE-0138): the editorial workflow / AI-assist types moved to
 * `@/modules/editorial` (their canonical bounded-context home — they model the
 * editorial workspace's workflow state and slide reviews). Publishing keeps
 * exposing them through its own public contract for blog/AI consumers, so this
 * forwards to the editorial public contract.
 *
 * Routing the dependency this way (publishing -> editorial) keeps the two module
 * barrels acyclic: editorial no longer imports the publishing barrel.
 */
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
} from "@/modules/editorial";
