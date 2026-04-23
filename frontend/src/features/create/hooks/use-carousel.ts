import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { STATUS_POLL_INTERVAL } from "@/constants/create";
import {
  carouselProjectResponseSchema,
  carouselStatusResponseSchema,
  carouselStreamEventSchema,
  type CarouselProjectResponse,
  type CarouselStatusResponse,
  type CarouselCreateRequest,
  type CarouselStreamEvent,
} from "@/schemas/carousel";

const CAROUSELS_KEY = "carousels";
const CAROUSEL_STATUS_KEY = "carousel-status";
const CAROUSEL_KEY = "carousel";

// Lifecycle markers emitted by the backend /stream route alongside
// real node names. When consumers see `end` or `error` the stream is
// finished and the EventSource can be closed.
const STREAM_EVENT_END = "end";
const STREAM_EVENT_ERROR = "error";

// Auto-reconnect tuning — long-running LLM calls can cause proxy/browser
// timeouts during phases with zero SSE events (e.g. drafting).
const MAX_STREAM_RETRIES = 20;
const BASE_RETRY_DELAY_MS = 1000;
const MAX_RETRY_DELAY_MS = 30000;

type GenerateArgs = {
  projectId: string;
  sources?: string[];
};

/** Create a new carousel project and return the created project. */
export function useCreateCarousel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CarouselCreateRequest): Promise<CarouselProjectResponse> => {
      return apiCall(
        API_ENDPOINTS.CAROUSELS,
        carouselProjectResponseSchema,
        {
          method: HTTP_METHODS.POST,
          body: JSON.stringify(data),
        }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CAROUSELS_KEY] });
    },
  });
}

/** Trigger the backend pipeline for an existing project. Long-running. */
export function useGenerateCarousel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ projectId, sources }: GenerateArgs): Promise<CarouselStatusResponse> => {
      return apiCall(
        API_ENDPOINTS.CAROUSEL_GENERATE(projectId),
        carouselStatusResponseSchema,
        {
          method: HTTP_METHODS.POST,
          body: JSON.stringify({ sources: sources ?? null }),
        }
      );
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [CAROUSEL_STATUS_KEY, variables.projectId] });
      queryClient.invalidateQueries({ queryKey: [CAROUSEL_KEY, variables.projectId] });
    },
  });
}

/**
 * Resume an interrupted pipeline from its last checkpoint.
 *
 * Returns the latest project snapshot. Idempotent-by-design nodes in
 * the backend graph (persist_slides, image_worker, export) short-
 * circuit on work that's already complete, so expensive API calls
 * like gpt-image-2 don't re-fire.
 */
export function useResumeCarousel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string): Promise<CarouselStatusResponse> => {
      return apiCall(
        API_ENDPOINTS.CAROUSEL_RESUME(projectId),
        carouselStatusResponseSchema,
        { method: HTTP_METHODS.POST }
      );
    },
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: [CAROUSEL_STATUS_KEY, projectId] });
      queryClient.invalidateQueries({ queryKey: [CAROUSEL_KEY, projectId] });
    },
  });
}

/**
 * Poll carousel generation status by ID. Kept as a fallback for
 * environments where SSE is blocked by a corporate proxy — the
 * workspace page prefers `useCarouselStream` but falls back to this
 * hook when streaming fails.
 */
export function useCarouselStatus(id: string | null) {
  return useQuery({
    queryKey: [CAROUSEL_STATUS_KEY, id],
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_STATUS(id as string),
        carouselStatusResponseSchema
      ),
    enabled: !!id,
    refetchInterval: STATUS_POLL_INTERVAL,
  });
}

/** Fetch carousel project by ID for workspace page. */
export function useCarouselProject(id: string | null) {
  return useQuery({
    queryKey: [CAROUSEL_KEY, id],
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_BY_ID(id as string),
        carouselProjectResponseSchema
      ),
    enabled: !!id,
  });
}

/**
 * State returned by `useCarouselStream`. Mirrors the shape of the
 * polling status response so consumers can use either interchangeably.
 */
export interface CarouselStreamState {
  /** Latest event received from the stream, or null before first message. */
  latestEvent: CarouselStreamEvent | null;
  /** True while the EventSource is live. False once the stream closed. */
  isStreaming: boolean;
  /** Non-null if the stream terminated with an `error` event or transport failure. */
  error: string | null;
  /** Close the stream eagerly (e.g. when navigating away). */
  close: () => void;
  /** Force an immediate reconnect (used after resume or manual retry). */
  reconnect: () => void;
}

function calculateBackoff(attempt: number): number {
  return Math.min(BASE_RETRY_DELAY_MS * 2 ** attempt, MAX_RETRY_DELAY_MS);
}

/**
 * Subscribe to `GET /api/carousels/{id}/stream` via EventSource and
 * keep the TanStack Query cache in sync with each event.
 *
 * EventSource is GET-only, so the backend route must accept GET.
 * When `enabled` is false or `id` is null the hook is a no-op. On every
 * `message` we:
 *   1. Parse + Zod-validate the event.
 *   2. Write the mirrored status shape into the `carousel-status` cache
 *      so components reading `useCarouselStatus` see the live values.
 *   3. Stash the raw event for consumers that want the node name.
 *
 * Auto-reconnect: long-running phases (drafting, image generation) can
 * drop the SSE connection. We retry with exponential backoff up to
 * `MAX_STREAM_RETRIES`. A successful event resets the retry budget.
 */
export function useCarouselStream(
  id: string | null,
  options: { enabled?: boolean } = {},
): CarouselStreamState {
  const { enabled = true } = options;
  const queryClient = useQueryClient();
  const [latestEvent, setLatestEvent] = useState<CarouselStreamEvent | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectKey, setReconnectKey] = useState(0);
  const sourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const close = (): void => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setIsStreaming(false);
  };

  const reconnect = (): void => {
    retryCountRef.current = 0;
    setReconnectKey((k) => k + 1);
  };

  useEffect(() => {
    if (!id || !enabled) {
      return;
    }

    // Browsers' EventSource only speaks GET. The backend /stream route
    // is a GET endpoint, so the connection works out of the box.
    const source = new EventSource(API_ENDPOINTS.CAROUSEL_STREAM(id));
    sourceRef.current = source;
    setIsStreaming(true);
    setError(null);

    source.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data);
        const result = carouselStreamEventSchema.safeParse(parsed);
        if (!result.success) {
          return;
        }
        const event = result.data;
        setLatestEvent(event);

        // A successful event resets the retry budget — the pipeline is
        // alive and making progress.
        retryCountRef.current = 0;

        // Keep the polling cache in sync so components that read
        // `useCarouselStatus` reflect the live event without polling.
        if (event.status !== undefined) {
          queryClient.setQueryData([CAROUSEL_STATUS_KEY, id], (prev: CarouselStatusResponse | undefined) => ({
            ...(prev ?? { id, error_message: null, updated_at: new Date().toISOString() }),
            id,
            status: event.status ?? prev?.status ?? "",
            phase_progress: event.phase_progress ?? prev?.phase_progress ?? null,
            error_message: event.error ?? prev?.error_message ?? null,
            updated_at: new Date().toISOString(),
          }));
        }

        if (event.node === STREAM_EVENT_END || event.node === STREAM_EVENT_ERROR) {
          // Pipeline finished or failed — close the stream and let the
          // consumer read the terminal event from `latestEvent`.
          if (event.node === STREAM_EVENT_ERROR && event.error) {
            setError(event.error);
          }
          queryClient.invalidateQueries({ queryKey: [CAROUSEL_KEY, id] });
          close();
        }
      } catch {
        // Malformed event — ignore and keep the stream open.
      }
    };

    source.onerror = () => {
      // EventSource auto-reconnects on network blips; we only surface
      // an error when the browser gives up and the readyState is CLOSED.
      if (source.readyState === EventSource.CLOSED) {
        close();
        if (retryCountRef.current < MAX_STREAM_RETRIES) {
          const delay = calculateBackoff(retryCountRef.current);
          retryCountRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => {
            setReconnectKey((k) => k + 1);
          }, delay);
        } else {
          setError("stream disconnected — max retries reached");
        }
      }
    };

    return close;
    // reconnectKey is intentionally omitted — it is the *trigger* for the
    // effect, not a value consumed inside it. Including it in deps would
    // cause a lint warning but not change behavior because the effect
    // already re-runs when reconnectKey changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, enabled, queryClient, reconnectKey]);

  return { latestEvent, isStreaming, error, close, reconnect };
}
