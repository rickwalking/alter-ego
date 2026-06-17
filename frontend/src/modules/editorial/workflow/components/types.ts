/**
 * Editorial workflow component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

export type BlogPostEditExtrasProps = {
  postId: string;
  title: string;
  status: string;
  bodyText: string;
  previousBodyText?: string;
  onScheduled?: () => void;
};

export type ReviewAssignmentPanelProps = {
  contentId: string;
  contentType: string;
  title: string;
  onAssigned?: () => void;
};

export type ScheduledPublishPickerProps = {
  postId: string;
  onScheduled?: () => void;
};

export type VersionDiffViewProps = {
  leftLabel: string;
  rightLabel: string;
  leftText: string;
  rightText: string;
};
