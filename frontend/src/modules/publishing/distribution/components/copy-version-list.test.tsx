import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type {
  CopyHistory,
  CopyVersionView,
} from "@/modules/publishing/distribution/hooks/types";
import { CopyVersionList } from "./copy-version-list";

/** Gherkin: tests/features/copy-version-history-ae0506.feature. */

function version(overrides: Partial<CopyVersionView>): CopyVersionView {
  return {
    version_number: 1,
    field: "caption",
    text: "Legenda gerada",
    author_id: null,
    author_name: null,
    created_at: "2026-10-22T12:00:00Z",
    restored_from: null,
    ...overrides,
  };
}

const VERSIONS: CopyVersionView[] = [
  version({
    version_number: 4,
    field: "linkedin_post_en",
    text: "EN post",
    author_id: "u1",
    author_name: "Pedro",
  }),
  version({
    version_number: 3,
    text: "Legenda restaurada",
    author_id: "u1",
    author_name: "Pedro",
    restored_from: 1,
  }),
  version({
    version_number: 2,
    text: "Legenda editada",
    author_id: "u1",
    author_name: "Pedro",
  }),
  version({ version_number: 1 }),
];

function history(overrides: Partial<CopyHistory> = {}): CopyHistory {
  return {
    versions: VERSIONS,
    loading: false,
    status: { kind: "idle" },
    restore: vi.fn(() => Promise.resolve()),
    ...overrides,
  };
}

describe("CopyVersionList (AE-0506)", () => {
  /** Scenario: The history lists the versions of the text under its editor */
  it("lists the caption versions newest first with who and when", () => {
    render(
      <CopyVersionList
        history={history()}
        fields={["caption"]}
        blocked={false}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("Version 3");
    expect(items[0]).toHaveTextContent("Pedro");
    expect(items[0]).toHaveTextContent("restored from version 1");
    expect(items[2]).toHaveTextContent("Generated text");
    expect(items[2]).toHaveTextContent("Legenda gerada");
    expect(screen.getAllByRole("time")[0]).toHaveAttribute(
      "datetime",
      "2026-10-22T12:00:00Z",
    );
    expect(
      screen.queryByRole("button", { name: "Restore version 3" }),
    ).not.toBeInTheDocument();
  });

  /** Scenario: The LinkedIn history shows the versions of both languages */
  it("labels each LinkedIn version with its language", () => {
    render(
      <CopyVersionList
        history={history()}
        fields={["linkedin_post_pt", "linkedin_post_en"]}
        blocked={false}
      />,
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("listitem")).toHaveTextContent("EN");
  });

  /** Scenario: Restoring a version sends it with the current lock version */
  it("restores an older version", () => {
    const current = history();
    render(
      <CopyVersionList
        history={current}
        fields={["caption"]}
        blocked={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Restore version 1" }));
    expect(current.restore).toHaveBeenCalledWith(1);
  });

  /** Scenario: A text with unsaved edits cannot be restored */
  it("waits for unsaved edits before a restore", () => {
    render(
      <CopyVersionList history={history()} fields={["caption"]} blocked />,
    );
    expect(
      screen.getByRole("button", { name: "Restore version 1" }),
    ).toBeDisabled();
    expect(
      screen.getByText("Save or discard the edit before restoring a version."),
    ).toBeInTheDocument();
  });

  /** Scenario: A refused restore explains why */
  it("shows why a restore was refused", () => {
    render(
      <CopyVersionList
        history={history({
          status: { kind: "error", errorKey: "copy.errors.captionPublished" },
        })}
        fields={["caption"]}
        blocked={false}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The caption is already published on Instagram",
    );
  });

  /** Scenario: Restoring a version sends it with the current lock version */
  it("shows the running restore and blocks the others", () => {
    render(
      <CopyVersionList
        history={history({ status: { kind: "restoring", versionNumber: 1 } })}
        fields={["caption"]}
        blocked={false}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Restore version 1" }),
    ).toHaveTextContent("Restoring…");
    expect(
      screen.getByRole("button", { name: "Restore version 2" }),
    ).toBeDisabled();
  });

  /** Scenario: The history lists the versions of the text under its editor */
  it("says when there is nothing yet, or while it loads", () => {
    const { rerender } = render(
      <CopyVersionList
        history={history({ versions: [], restore: undefined })}
        fields={["caption"]}
        blocked
      />,
    );
    expect(screen.getByText("No saved versions yet.")).toBeInTheDocument();
    rerender(
      <CopyVersionList
        history={history({ versions: [], loading: true })}
        fields={["caption"]}
        blocked={false}
      />,
    );
    expect(screen.getByText("Loading the history…")).toBeInTheDocument();
  });
});
