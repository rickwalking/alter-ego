import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  carouselProjectResponseSchema,
  carouselStatusResponseSchema,
  carouselStreamEventSchema,
  type CarouselProjectResponse,
  type CarouselStatusResponse,
  type CarouselCreateRequest,
  type CarouselStreamEvent,
} from "@/schemas/carousel";
import {
  carouselKeys,
  carouselProjectOptions,
  carouselStatusOptions,
} from "@/features/carousel/queries";

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

interface StreamState {
  key: string | null;
  latestEvent: CarouselStreamEvent | null;
  closed: boolean;
  error: string | null;
}

function createStreamState(key: string | null): StreamState {
  return {
    key,
    latestEvent: null,
    closed: false,
    error: null,
  };
}

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
    onSuccess: (project) => {
      queryClient.setQueryData(carouselKeys.detail(project.id), project);
      queryClient.setQueryData<CarouselProjectResponse[]>(
        carouselKeys.list(),
        (previous) =>
          previous
            ? [project, ...previous.filter((item) => item.id !== project.id)]
            : previous,
      );
      queryClient.invalidateQueries({ queryKey: carouselKeys.list() });
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
    onSuccess: (status, variables) => {
      queryClient.setQueryData(carouselKeys.status(variables.projectId), status);
      queryClient.invalidateQueries({
        queryKey: carouselKeys.status(variables.projectId),
      });
      queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(variables.projectId),
      });
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
    onSuccess: (status, projectId) => {
      queryClient.setQueryData(carouselKeys.status(projectId), status);
      queryClient.invalidateQueries({ queryKey: carouselKeys.status(projectId) });
      queryClient.invalidateQueries({ queryKey: carouselKeys.detail(projectId) });
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
  return useQuery(carouselStatusOptions(id));
}

/** Fetch carousel project by ID for workspace page. */
export function useCarouselProject(id: string | null) {
  return useQuery(carouselProjectOptions(id));
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
  const [reconnectKey, setReconnectKey] = useState(0);
  const streamKey = id && enabled ? `${id}:${reconnectKey}` : null;
  const [streamState, setStreamState] = useState(() =>
    createStreamState(streamKey),
  );
  const currentStreamState =
    streamState.key === streamKey ? streamState : createStreamState(streamKey);
  const sourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  if (streamState.key !== streamKey) {
    setStreamState(currentStreamState);
  }

  const close = useCallback((): void => {
    const key = streamKey;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setStreamState((state) =>
      state.key === key ? { ...state, closed: true } : state,
    );
  }, [streamKey]);

  const reconnect = (): void => {
    retryCountRef.current = 0;
    setReconnectKey((k) => k + 1);
  };

  useLayoutEffect(() => {
    if (!id || !enabled) {
      return;
    }

    // Browsers' EventSource only speaks GET. The backend /stream route
    // is a GET endpoint, so the connection works out of the box.
    const source = new EventSource(API_ENDPOINTS.CAROUSEL_STREAM(id));
    sourceRef.current = source;

    source.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data);
        const result = carouselStreamEventSchema.safeParse(parsed);
        if (!result.success) {
          return;
        }
        const event = result.data;
        setStreamState((state) =>
          state.key === streamKey ? { ...state, latestEvent: event } : state,
        );

        // A successful event resets the retry budget — the pipeline is
        // alive and making progress.
        retryCountRef.current = 0;

        // Keep the polling cache in sync so components that read
        // `useCarouselStatus` reflect the live event without polling.
        if (event.status !== undefined) {
          queryClient.setQueryData(carouselKeys.status(id), (prev: CarouselStatusResponse | undefined) => ({
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
            setStreamState((state) =>
              state.key === streamKey
                ? { ...state, error: event.error ?? null }
                : state,
            );
          }
          queryClient.invalidateQueries({ queryKey: carouselKeys.detail(id) });
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
          setStreamState((state) =>
            state.key === streamKey
              ? { ...state, error: "stream disconnected — max retries reached" }
              : state,
          );
        }
      }
    };

    return close;
  }, [id, enabled, queryClient, reconnectKey, streamKey, close]);

  return {
    latestEvent: currentStreamState.latestEvent,
    isStreaming: streamKey !== null && !currentStreamState.closed,
    error: currentStreamState.error,
    close,
    reconnect,
  };
}
