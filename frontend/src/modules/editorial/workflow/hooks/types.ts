import type { RefObject } from "react";
import type { QueryClient } from "@tanstack/react-query";
import type { QueueAction } from "@/constants/workflow";
import type { QueueBoard } from "@/schemas/generation-queue";
import type {
  CarouselReprocessCapability,
  ManualReprocessResponse,
} from "@/schemas/carousel-reprocess";
/**
 * Editorial workflow hook data-shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention (
 * `frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the hook `.ts` files.
 */

export interface CalendarItem {
  id: string;
  content_type: string;
  title: string;
  status: string;
  event_date: string;
  is_scheduled?: boolean;
  phase?: string;
  phase_status?: string;
}

export interface ContentCalendar {
  items: CalendarItem[];
  start: string;
  end: string;
  total: number;
}

export interface KanbanCard {
  id: string;
  title: string;
  topic: string;
  current_phase: string;
  phase_status: string;
  workflow_status?: string | null;
  updated_at: string | null;
  /** The caller may archive or restore it (owner or admin, not a reviewer). */
  can_archive?: boolean;
  /** Why the archive rules refuse it now, if they do. */
  archive_refusal?: string | null;
}

export interface KanbanColumn {
  phase: string;
  cards: KanbanCard[];
}

export interface WorkflowKanban {
  columns: KanbanColumn[];
}

export interface WorkflowPostActionMessages {
  success: string;
  failed: string;
}

export interface WorkflowPostActionResult {
  submitting: boolean;
  message: string | null;
  post: (url: string, body: object) => Promise<void>;
}

export interface GenerationQueueMaintenanceState {
  processPending: boolean;
  processError: string | null;
  processQueue: () => Promise<void>;
}

/** The queue panel's data, the button in flight and the last button's error. */
export interface GenerationQueueState extends GenerationQueueMaintenanceState {
  board: QueueBoard | null;
  error: string | null;
  pending: string | null;
  actionError: string | null;
  act: (action: QueueAction, id: string) => Promise<void>;
}

export interface GenerationQueueMaintenanceDeps {
  load: () => Promise<void>;
  translate: (key: string) => string;
  processInFlightRef: RefObject<boolean>;
  setProcessPending: (pending: boolean) => void;
  setProcessError: (message: string | null) => void;
}

export interface UseCarouselReprocessOptions {
  projectId: string;
  enabled: boolean;
  fallbackExpectedVersion?: number;
  refreshWorkflow: () => Promise<unknown>;
}

export interface CarouselReprocessRequest {
  expectedVersion: number;
  runId: string | null;
}

export interface CarouselReprocessErrorDeps {
  projectId: string;
  queryClient: QueryClient;
  refreshWorkflow: () => Promise<unknown>;
  translate: (key: string) => string;
  setActionError: (message: string | null) => void;
}

export interface CarouselReprocessRunDeps extends CarouselReprocessErrorDeps {
  enabled: boolean;
  capability: CarouselReprocessCapability | null;
  fallbackExpectedVersion?: number;
  inFlightRef: RefObject<boolean>;
  setPending: (pending: boolean) => void;
  mutateAsync: (
    input: CarouselReprocessRequest,
  ) => Promise<ManualReprocessResponse>;
}

export interface CarouselReprocessActionState {
  pending: boolean;
  canSubmit: boolean;
  actionError: string | null;
  reprocess: () => Promise<void>;
}

export interface CarouselReprocessState {
  capability: CarouselReprocessCapability | null;
  pending: boolean;
  forbidden: boolean;
  canSubmit: boolean;
  error: string | null;
  reprocess: () => Promise<void>;
}
