import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import pt from "@/i18n/locales/pt.json";
import type { Document } from "@/schemas/knowledge";
import { DocumentCard } from "./document-card";

const NOW = new Date("2026-10-22T12:00:00Z");

function doc(overrides: Partial<Document>): Document {
  return {
    id: "d1",
    title: "my_resume.pdf",
    status: "completed",
    scope: "personal",
    is_public: false,
    metadata: {},
    chunk_count: 4,
    created_at: "2026-06-02T00:00:00Z",
    updated_at: "2026-10-22T11:58:00Z",
    error_message: null,
    ...overrides,
  };
}

describe("DocumentCard processing state", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  // Scenario: A failed document shows its reason and a Retry button
  it("shows the failure reason and retries", () => {
    const onRetry = vi.fn();
    render(
      <DocumentCard
        document={doc({
          status: "failed",
          chunk_count: 0,
          error_message: "RuntimeError: embedding service unavailable",
        })}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(
      screen.getByText("RuntimeError: embedding service unavailable"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  // Scenario: A document stuck in processing is shown as stale with Retry
  it.each([["pending"], ["processing"]])(
    "flags a %s document untouched for over 10 minutes as stale",
    (status) => {
      vi.useFakeTimers({ toFake: ["Date"] });
      vi.setSystemTime(NOW);
      render(
        <DocumentCard
          document={doc({
            status,
            chunk_count: 0,
            updated_at: "2026-06-02T00:00:00Z",
          })}
          onRetry={vi.fn()}
        />,
      );
      expect(
        screen.getByText("Processing did not finish."),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
    },
  );

  // Scenario: A fresh or completed document offers no Retry
  it.each([
    ["completed", "2026-06-02T00:00:00Z"],
    ["pending", "2026-10-22T11:58:00Z"],
  ])("offers no retry for a %s document", (status, updatedAt) => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
    render(
      <DocumentCard
        document={doc({ status, updated_at: updatedAt })}
        onRetry={vi.fn()}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Retry" }),
    ).not.toBeInTheDocument();
  });

  // Scenario: Status and labels are translated
  it("labels status, chunks and delete from the messages", () => {
    render(<DocumentCard document={doc({})} onDelete={vi.fn()} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("4 chunks")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete document: my_resume.pdf" }),
    ).toBeInTheDocument();
    expect(pt.knowledge.document.status.completed).toBe("Concluído");
    expect(pt.knowledge.document.retry).toBe("Tentar de novo");
  });
});
