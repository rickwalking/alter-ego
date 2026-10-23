/**
 * The upload and new-document forms carry the chosen scope.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { uploadFormData } from "../hooks/use-upload";
import { DocumentForm } from "./document-form";
import { FileUpload } from "./file-upload";

const mutate = vi.fn();
vi.mock("../hooks/use-upload", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../hooks/use-upload")>()),
  useUploadDocument: () => ({
    isSuccess: false,
    isPending: false,
    isError: false,
    mutate,
    error: null,
  }),
}));

function pickFile(): void {
  fireEvent.change(screen.getByLabelText(en.knowledge.upload.selectFile), {
    target: { files: [new File(["x"], "bio.md", { type: "text/markdown" })] },
  });
}

function chooseScope(label: string): void {
  fireEvent.click(screen.getByRole("radio", { name: label }));
}

describe("Scope at upload", () => {
  beforeEach(() => {
    mutate.mockReset();
  });

  /** Scenario: An upload is personal unless I choose public */
  it("uploads as personal by default", () => {
    render(<FileUpload />);
    pickFile();
    expect(
      screen.getByRole("radio", { name: en.knowledge.scope.personal }),
    ).toBeChecked();
    fireEvent.click(screen.getByText(en.knowledge.upload.uploadButton));
    expect(mutate.mock.calls[0]![0]).toMatchObject({ scope: "personal" });
  });

  /** Scenario: An upload is personal unless I choose public */
  it("uploads as public when Public is chosen", () => {
    render(<FileUpload />);
    pickFile();
    chooseScope(en.knowledge.scope.public);
    fireEvent.click(screen.getByText(en.knowledge.upload.uploadButton));
    expect(mutate.mock.calls[0]![0]).toMatchObject({ scope: "public" });
  });

  /** Scenario: An upload is personal unless I choose public */
  it("sends the scope and the matching is_public as multipart fields", () => {
    const file = new File(["x"], "bio.md");
    const personal = uploadFormData({ file, scope: "personal" });
    expect(personal.get("scope")).toBe("personal");
    expect(personal.get("is_public")).toBe("false");
    const shared = uploadFormData({
      file,
      title: "Bio",
      tags: "cv",
      scope: "public",
    });
    expect(shared.get("scope")).toBe("public");
    expect(shared.get("is_public")).toBe("true");
    expect(shared.get("title")).toBe("Bio");
    expect(shared.get("tags")).toBe("cv");
  });

  /** Scenario: An upload is personal unless I choose public */
  it("explains what the scopes feed", () => {
    render(<FileUpload />);
    pickFile();
    expect(screen.getByText(en.knowledge.scope.hint)).toBeInTheDocument();
    expect(pt.knowledge.scope.hint).toContain(
      "O chat público lê só o que é Público",
    );
  });
});

describe("Scope of a typed document", () => {
  /** Scenario: A typed document takes the chosen scope */
  it("creates the document with the chosen scope", () => {
    const onSubmit = vi.fn();
    render(<DocumentForm onSubmit={onSubmit} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(en.knowledge.form.title), {
      target: { value: "Bio" },
    });
    fireEvent.change(screen.getByLabelText(en.knowledge.form.content), {
      target: { value: "Pedro builds things." },
    });
    chooseScope(en.knowledge.scope.public);
    fireEvent.click(
      screen.getByRole("button", { name: en.knowledge.form.submit }),
    );
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ scope: "public", is_public: true }),
    );
  });

  /** Scenario: A typed document takes the chosen scope */
  it("creates a personal document by default", () => {
    const onSubmit = vi.fn();
    render(<DocumentForm onSubmit={onSubmit} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(en.knowledge.form.title), {
      target: { value: "Notes" },
    });
    fireEvent.change(screen.getByLabelText(en.knowledge.form.content), {
      target: { value: "Private." },
    });
    fireEvent.click(
      screen.getByRole("button", { name: en.knowledge.form.submit }),
    );
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ scope: "personal", is_public: false }),
    );
  });
});
