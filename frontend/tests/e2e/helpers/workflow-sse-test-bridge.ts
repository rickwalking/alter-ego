/** Playwright helpers to inject workflow SSE events into the active EventSource. */

import type { Page } from "@playwright/test";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_SSE_EVENTS,
} from "../../../src/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "../../../src/constants/workflow";

const WORKFLOW_SSE_BRIDGE_KEY = "__emitWorkflowSse";

type SseListener = (event: MessageEvent<string>) => void;

export async function installWorkflowSseTestBridge(page: Page): Promise<void> {
  await page.addInitScript((bridgeKey) => {
    const originalEventSource = window.EventSource;
    let activeSource: EventSource | null = null;
    const listenersBySource = new WeakMap<
      EventSource,
      Map<string, SseListener[]>
    >();

    function trackListener(
      source: EventSource,
      eventType: string,
      listener: SseListener,
    ): void {
      const listenersByType =
        listenersBySource.get(source) ?? new Map<string, SseListener[]>();
      const handlers = listenersByType.get(eventType) ?? [];
      handlers.push(listener);
      listenersByType.set(eventType, handlers);
      listenersBySource.set(source, listenersByType);
    }

    const EventSourceProxy = function EventSourceProxy(
      url: string | URL,
      eventSourceInitDict?: EventSourceInit,
    ): EventSource {
      const source = new originalEventSource(url, eventSourceInitDict);
      activeSource = source;
      listenersBySource.set(source, new Map<string, SseListener[]>());

      const originalAddEventListener = source.addEventListener.bind(source);
      source.addEventListener = ((
        type: string,
        listener: EventListenerOrEventListenerObject,
        options?: boolean | AddEventListenerOptions,
      ): void => {
        if (typeof listener === "function") {
          trackListener(source, type, listener as SseListener);
        }
        originalAddEventListener(type, listener, options);
      }) as typeof source.addEventListener;

      return source;
    } as unknown as typeof EventSource;

    Object.defineProperty(EventSourceProxy, "CONNECTING", {
      value: originalEventSource.CONNECTING,
    });
    Object.defineProperty(EventSourceProxy, "OPEN", {
      value: originalEventSource.OPEN,
    });
    Object.defineProperty(EventSourceProxy, "CLOSED", {
      value: originalEventSource.CLOSED,
    });
    Object.defineProperty(EventSourceProxy, "prototype", {
      value: originalEventSource.prototype,
    });

    window.EventSource = EventSourceProxy;

    (
      window as unknown as Record<
        string,
        (eventType: string, payload: Record<string, unknown>) => void
      >
    )[bridgeKey] = (eventType: string, payload: Record<string, unknown>): void => {
      if (!activeSource) {
        return;
      }
      const event = {
        data: JSON.stringify(payload),
      } as MessageEvent<string>;
      const listenersByType = listenersBySource.get(activeSource);
      const typedHandlers = listenersByType?.get(eventType) ?? [];
      typedHandlers.forEach((handler) => {
        handler(event);
      });
      if (activeSource.onmessage) {
        activeSource.onmessage(event);
      }
    };
  }, WORKFLOW_SSE_BRIDGE_KEY);
}

export async function emitWorkflowSseEvent(
  page: Page,
  eventType: string,
  payload: Record<string, unknown>,
): Promise<void> {
  await page.evaluate(
    ([bridgeKey, type, data]) => {
      const emit = (
        window as unknown as Record<
          string,
          (eventName: string, eventPayload: Record<string, unknown>) => void
        >
      )[bridgeKey];
      emit?.(type, data);
    },
    [WORKFLOW_SSE_BRIDGE_KEY, eventType, payload] as const,
  );
}

export function buildOutlineReviewRequiredPayload(
  projectId: string,
  outline: Array<Record<string, unknown>>,
): Record<string, unknown> {
  return {
    event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
    project_id: projectId,
    phase: EDITORIAL_PHASES.OUTLINE,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    gate_payload: {
      current_phase: EDITORIAL_PHASES.OUTLINE,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [
        {
          source: "E2E security report",
          summary: "Synthetic research findings for Playwright E2E validation.",
        },
      ],
      outline,
      slide_drafts: [],
    },
  };
}
