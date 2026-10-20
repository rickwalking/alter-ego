import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { v2Document } from "../editor.test-utils";
import { snapshotText, VersionHistorySidebar } from "./version-history-sidebar";

// Scenarios: Saving appends a version snapshot visible in the sidebar /
// Restoring a version loads it into the editor /
// A failed restore shows its error in the version sidebar (AE-0438, F-11)
// (tests/features/blog_editor_ae0424.feature, blog_editor_errors_ae0438.feature)

describe("VersionHistorySidebar", () => {
  it("lists versions, previews the snapshot and restores", () => {
    const onRestore = vi.fn();
    render(
      <VersionHistorySidebar
        versions={[
          { version_number: 1, title: "T1", snapshot: v2Document() },
          { version_number: 2 },
        ]}
        loading={false}
        currentText="Agora"
        disabled={false}
        onRestore={onRestore}
      />,
    );
    expect(screen.getByText("T1")).toBeInTheDocument();
    const labels = screen
      .getAllByText(/^Version \d$/)
      .map((el) => el.textContent);
    expect(labels).toEqual(["Version 2", "Version 1"]);
    fireEvent.click(screen.getByText("Version 1"));
    expect(screen.getByText(/Corpo um/)).toBeInTheDocument();
    expect(screen.getByText("Agora")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Restore this version" }),
    );
    expect(onRestore).toHaveBeenCalledWith(1);
  });

  it("shows the restore error inside the sidebar", async () => {
    const onRestore = vi.fn().mockResolvedValue({
      kind: "validation",
      detail: "blog_version_empty",
    });
    render(
      <VersionHistorySidebar
        versions={[{ version_number: 1, snapshot: v2Document() }]}
        loading={false}
        currentText="Agora"
        disabled={false}
        onRestore={onRestore}
      />,
    );
    fireEvent.click(screen.getByText("Version 1"));
    fireEvent.click(
      screen.getByRole("button", { name: "Restore this version" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "This version has no content",
      ),
    );
  });

  it("shows the loading and empty states", () => {
    const { rerender } = render(
      <VersionHistorySidebar
        versions={[]}
        loading
        currentText=""
        disabled
        onRestore={vi.fn()}
      />,
    );
    expect(screen.getByText("Loading versions…")).toBeInTheDocument();
    rerender(
      <VersionHistorySidebar
        versions={[]}
        loading={false}
        currentText=""
        disabled
        onRestore={vi.fn()}
      />,
    );
    expect(screen.getByText("No saved versions yet.")).toBeInTheDocument();
  });

  it("clips long previews and reads only v2 snapshots", () => {
    expect(snapshotText({ markdown: "x" })).toBe("");
    expect(snapshotText(undefined)).toBe("");
    expect(snapshotText(v2Document())).toBe(
      "Um\n\nCorpo um\n\nDois\n\nCorpo dois\n\nCorpo três",
    );
    render(
      <VersionHistorySidebar
        versions={[{ version_number: 3, snapshot: v2Document() }]}
        loading={false}
        currentText={"y".repeat(500)}
        disabled={false}
        onRestore={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Version 3"));
    expect(screen.getByText(`${"y".repeat(400)}…`)).toBeInTheDocument();
  });
});
