/**
 * Knowledge file upload, pinned while it was split into a form hook
 * and presentational parts.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FileUpload } from "./file-upload";

const translate = (key: string): string => key;
vi.mock("next-intl", () => ({
  useTranslations: () => translate,
}));

const mutate = vi.fn();
const uploadState = { isSuccess: false, isPending: false, isError: false };
vi.mock("../hooks/use-upload", () => ({
  useUploadDocument: () => ({ ...uploadState, mutate, error: null }),
}));

function pickFile(file: File): void {
  fireEvent.change(screen.getByLabelText("selectFile"), {
    target: { files: [file] },
  });
}

describe("FileUpload (AE-0446)", () => {
  beforeEach(() => {
    mutate.mockReset();
    uploadState.isSuccess = false;
  });

  it("shows the picked file and defaults the title to its name", () => {
    render(<FileUpload />);
    pickFile(new File(["x"], "notes.md", { type: "text/markdown" }));
    expect(screen.getByText("notes.md")).toBeInTheDocument();
    expect(screen.getByLabelText("fields.title")).toHaveValue("notes");
  });

  it("rejects an unsupported file type", () => {
    render(<FileUpload />);
    pickFile(new File(["x"], "photo.png", { type: "image/png" }));
    expect(screen.getByText("error.fileType")).toBeInTheDocument();
    expect(screen.getByText("uploadButton").closest("button")).toBeDisabled();
  });

  it("uploads with the title and tags", () => {
    render(<FileUpload />);
    pickFile(new File(["x"], "notes.md", { type: "text/markdown" }));
    fireEvent.change(screen.getByLabelText("fields.tags"), {
      target: { value: "ai" },
    });
    fireEvent.click(screen.getByText("uploadButton"));
    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate.mock.calls[0]![0]).toMatchObject({
      title: "notes",
      tags: "ai",
    });
  });

  it("shows the success panel once uploaded", () => {
    uploadState.isSuccess = true;
    render(<FileUpload />);
    expect(screen.getByText("success.title")).toBeInTheDocument();
  });

  it("labels the drop area, file input and remove button from the translations", () => {
    // Scenario: The knowledge upload labels come from the translations
    render(<FileUpload />);
    expect(
      screen.getByRole("region", { name: "dropZone" }),
    ).toBeInTheDocument();
    pickFile(new File(["x"], "notes.md", { type: "text/markdown" }));
    expect(
      screen.getByRole("button", { name: "removeFile" }),
    ).toBeInTheDocument();
  });

  it("labels the upload progress from the translations", () => {
    // Scenario: The knowledge upload labels come from the translations
    uploadState.isPending = true;
    render(<FileUpload />);
    expect(
      screen.getByRole("status", { name: "progress" }),
    ).toBeInTheDocument();
    uploadState.isPending = false;
  });
});
