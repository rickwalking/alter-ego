import { NextIntlClientProvider } from "next-intl";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import type { GenerationLogView } from "@/modules/editorial";
import type { GenerationLogEvent } from "@/schemas/carousel-generation-log";
import { CreateGenerationLog } from "./create-generation-log";

vi.mock("next-intl", async (importOriginal) => importOriginal());

const newerRunId = "11111111-1111-1111-1111-111111111111";
const olderRunId = "33333333-3333-3333-3333-333333333333";

interface EventFixture {
  id: string;
  runId: string;
  type: string;
  phase: string | null;
  occurredAt: string;
}

function event({
  id,
  runId,
  type,
  phase,
  occurredAt,
}: EventFixture): GenerationLogEvent {
  const failed = type === "content_gate";
  const details: GenerationLogEvent["details"] = failed
    ? { violation_count: 2, blocking_count: 1 }
    : { size: "1536x1024", model: "gpt-image-2" };
  return {
    id,
    generation_run_id: runId,
    event_type: type,
    phase,
    outcome: failed ? "failed" : "succeeded",
    occurred_at: occurredAt,
    duration_ms: failed ? null : 1250,
    attempt: 1,
    error_code: failed ? "content_gate_blocked" : null,
    message_code: failed ? "phase_failed" : "phase_succeeded",
    details,
    langfuse_trace_id: failed ? null : "b".repeat(32),
    langfuse_trace_url: failed
      ? null
      : `https://cloud.langfuse.com/project/p1/traces/${"b".repeat(32)}`,
  };
}

function view(overrides: Partial<GenerationLogView> = {}): GenerationLogView {
  return {
    data: {
      pages: [
        {
          project_id: "p1",
          next_cursor: "cursor-1",
          runs: [
            {
              id: newerRunId,
              kind: "workflow_resume",
              status: "dead_letter",
              queued_at: "2026-10-26T12:00:00Z",
              started_at: "2026-10-26T12:00:01Z",
              finished_at: "2026-10-26T12:01:00Z",
              duration_ms: 59000,
              attempts: 2,
              error_code: "transient",
            },
            {
              id: olderRunId,
              kind: "autopilot_drive",
              status: "succeeded",
              queued_at: "2026-10-25T12:00:00Z",
              started_at: "2026-10-25T12:00:01Z",
              finished_at: "2026-10-25T12:01:00Z",
              duration_ms: 59000,
              attempts: 1,
              error_code: null,
            },
          ],
          events: [
            event({
              id: "e3",
              runId: newerRunId,
              type: "content_gate",
              phase: "content",
              occurredAt: "2026-10-26T12:00:50Z",
            }),
            event({
              id: "e2",
              runId: newerRunId,
              type: "image_job_succeeded",
              phase: "images",
              occurredAt: "2026-10-26T12:00:40Z",
            }),
            event({
              id: "e1",
              runId: olderRunId,
              type: "run_succeeded",
              phase: null,
              occurredAt: "2026-10-25T12:01:00Z",
            }),
          ],
        },
      ],
      pageParams: [undefined],
    },
    isLoading: false,
    isError: false,
    isFetchingNextPage: false,
    hasNextPage: true,
    fetchNextPage: vi.fn(() => Promise.resolve(undefined)),
    ...overrides,
  };
}

function renderLog(query: GenerationLogView, locale = "en"): void {
  render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "pt" ? pt : en}
    >
      <CreateGenerationLog query={query} />
    </NextIntlClientProvider>,
  );
}

describe("CreateGenerationLog", () => {
  /** Scenario: Generation log groups runs and phases accessibly */
  it("groups newest runs and phases with accessible failures and durations", async () => {
    const user = userEvent.setup();
    const query = view();
    renderLog(query);
    const log = screen.getByRole("log", { name: "Generation log" });
    const runs = within(log).getAllByRole("group");
    const newer = within(log)
      .getByText(/Workflow resume/)
      .closest("details");
    const older = within(log)
      .getByText(/Autopilot drive/)
      .closest("details");

    expect(newer).toHaveAttribute("open");
    expect(older).not.toHaveAttribute("open");
    expect(newer).toHaveTextContent("Attempts: 2");
    expect(newer).toHaveTextContent("Attempt 1");
    expect(newer).toHaveTextContent("Failed");
    expect(newer).toHaveTextContent("Content gate");
    expect(newer).toHaveTextContent("2 violations");
    expect(newer).toHaveTextContent("1.3 s");
    expect(newer?.querySelector(".tabular-nums")).toHaveClass("text-right");
    expect(runs.length).toBeGreaterThanOrEqual(2);

    const olderSummary = within(older as HTMLElement).getByText(
      /Autopilot drive/,
    );
    olderSummary.focus();
    await user.keyboard("{Enter}");
    expect(olderSummary).toHaveFocus();
    expect(older).toHaveAttribute("open");
    await user.click(screen.getByRole("button", { name: "Load more" }));
    expect(query.fetchNextPage).toHaveBeenCalledTimes(1);
    expect(
      within(newer as HTMLElement).getByRole("link", {
        name: "Open Langfuse trace",
      }),
    ).toHaveAttribute("target", "_blank");
  });

  /** Scenario: Generation log groups runs and phases accessibly */
  it("uses safe raw-code fallbacks for future run states", () => {
    const query = view();
    const firstRun = query.data?.pages[0]?.runs[0];
    if (!firstRun) {
      throw new Error("missing fixture data");
    }
    firstRun.kind = "future_kind";
    firstRun.status = "future_status";
    renderLog(query);

    expect(screen.getByText(/future_kind, future_status/)).toBeInTheDocument();
  });

  /** Scenario: Generation log supports empty error and trace states */
  it("shows localized empty and preserves entries on refresh errors", () => {
    const empty = view({
      data: {
        pages: [
          {
            project_id: "p1",
            next_cursor: null,
            runs: [],
            events: [],
          },
        ],
        pageParams: [undefined],
      },
      hasNextPage: false,
    });
    const { rerender } = render(
      <NextIntlClientProvider locale="pt" messages={pt}>
        <CreateGenerationLog query={empty} />
      </NextIntlClientProvider>,
    );
    expect(screen.getByText("Registro de geração")).toBeInTheDocument();
    expect(
      screen.getByText("Nenhum evento de geração ainda."),
    ).toBeInTheDocument();

    rerender(
      <NextIntlClientProvider locale="pt" messages={pt}>
        <CreateGenerationLog query={{ ...empty, isError: true }} />
      </NextIntlClientProvider>,
    );
    expect(
      screen.getByText("Não foi possível carregar o registro de geração."),
    ).toBeInTheDocument();

    rerender(
      <NextIntlClientProvider locale="pt" messages={pt}>
        <CreateGenerationLog query={view({ isError: true })} />
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Execução do autopilot/)).toBeInTheDocument();
  });
});
