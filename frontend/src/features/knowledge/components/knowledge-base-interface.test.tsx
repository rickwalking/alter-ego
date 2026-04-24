import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test/utils";
import { KnowledgeBaseInterface } from "./knowledge-base-interface";

const knowledgeMocks = vi.hoisted(() => ({
  documents: [
    {
      id: "doc-1",
      title: "Document 1",
      content: "Content 1",
      metadata: { tags: ["one"] },
      created_at: "2026-04-20T00:00:00Z",
      updated_at: "2026-04-20T00:00:00Z",
    },
    {
      id: "doc-2",
      title: "Document 2",
      content: "Content 2",
      metadata: { tags: ["two"] },
      created_at: "2026-04-21T00:00:00Z",
      updated_at: "2026-04-21T00:00:00Z",
    },
  ],
  createDocument: vi.fn(),
  deleteDocument: vi.fn(),
}));

vi.mock("../hooks/use-documents", () => ({
  useDocuments: () => ({
    data: knowledgeMocks.documents,
    isLoading: false,
  }),
  useCreateDocument: () => ({
    mutate: knowledgeMocks.createDocument,
  }),
  useDeleteDocument: () => ({
    mutate: knowledgeMocks.deleteDocument,
  }),
}));

// Mock child components
vi.mock("@/components/layout", () => ({
  Container: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="container" className={className}>
      {children}
    </div>
  ),
}));

vi.mock("@/components/ui/card", () => ({
  Card: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card">{children}</div>
  ),
  CardHeader: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-header">{children}</div>
  ),
  CardContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-content">{children}</div>
  ),
  CardTitle: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-title">{children}</div>
  ),
}));

vi.mock("./document-list", () => ({
  DocumentList: ({
    documents,
    onCreateNew,
    onUploadNew,
  }: {
    documents: unknown[];
    onCreateNew: () => void;
    onUploadNew: () => void;
  }) => (
    <div data-testid="document-list">
      <div data-testid="document-count">{documents.length}</div>
      <button data-testid="create-new-btn" onClick={onCreateNew}>
        Create New
      </button>
      <button data-testid="upload-new-btn" onClick={onUploadNew}>
        Upload New
      </button>
    </div>
  ),
}));

vi.mock("./document-form", () => ({
  DocumentForm: ({
    document,
    onSubmit,
    onCancel,
  }: {
    document?: unknown;
    onSubmit: (data: unknown) => void;
    onCancel: () => void;
  }) => (
    <div data-testid="document-form">
      <div data-testid="form-mode">{document ? "edit" : "create"}</div>
      <button data-testid="form-submit" onClick={() => onSubmit({ title: "Test", content: "Content", tags: [] })}>
        Submit
      </button>
      <button data-testid="form-cancel" onClick={onCancel}>
        Cancel
      </button>
    </div>
  ),
}));

vi.mock("./file-upload", () => ({
  FileUpload: ({
    onUploadComplete,
    onCancel,
  }: {
    onUploadComplete: () => void;
    onCancel: () => void;
  }) => (
    <div data-testid="file-upload">
      <button data-testid="upload-complete" onClick={onUploadComplete}>
        Complete upload
      </button>
      <button data-testid="upload-cancel" onClick={onCancel}>
        Cancel upload
      </button>
    </div>
  ),
}));

// Mock generateId
vi.mock("@/lib/utils", async () => ({
  generateId: vi.fn(() => "new-id-123"),
  formatDate: vi.fn(() => "Jan 1, 2024"),
  cn: (...inputs: (string | undefined | false | null)[]) =>
    inputs.filter(Boolean).join(" "),
}));

describe("KnowledgeBaseInterface Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    knowledgeMocks.createDocument.mockImplementation((_data, options) => {
      options?.onSuccess?.();
    });
  });

  describe("Given the KnowledgeBaseInterface is rendered", () => {
    describe("When the component is displayed", () => {
      it("Then the page title should be visible", () => {
        render(<KnowledgeBaseInterface />);
        expect(screen.getByRole("heading", { name: /knowledge base/i })).toBeInTheDocument();
      });

      it("Then the page description should be visible", () => {
        render(<KnowledgeBaseInterface />);
        expect(screen.getByText(/manage your documents and information/i)).toBeInTheDocument();
      });

      it("Then the document list should be visible by default", () => {
        render(<KnowledgeBaseInterface />);
        expect(screen.getByTestId("document-list")).toBeInTheDocument();
      });

      it("Then initial documents should be loaded", () => {
        render(<KnowledgeBaseInterface />);
        expect(screen.getByTestId("document-count")).toHaveTextContent("2");
      });
    });

    describe("When the Create New button is clicked", () => {
      it("Then the document form should be displayed in create mode", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        expect(screen.getByTestId("document-form")).toBeInTheDocument();
        expect(screen.getByTestId("form-mode")).toHaveTextContent("create");
      });

      it("Then the document list should be hidden", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        expect(screen.queryByTestId("document-list")).not.toBeInTheDocument();
      });

      it("Then the form should be inside a card", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        expect(screen.getByTestId("card")).toBeInTheDocument();
      });

      it("Then the card title should indicate creating a new document", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        expect(screen.getByTestId("card-title")).toHaveTextContent(/create new document/i);
      });
    });

    describe("When upload is selected", () => {
      it("Then the upload form should be displayed", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("upload-new-btn"));
        expect(screen.getByTestId("file-upload")).toBeInTheDocument();
      });

      it("Then the card title should indicate uploading a document", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("upload-new-btn"));
        expect(screen.getByTestId("card-title")).toHaveTextContent(/upload document/i);
      });
    });

    describe("When the form is submitted for creating", () => {
      it("Then the create mutation should be called", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        await user.click(screen.getByTestId("form-submit"));

        expect(knowledgeMocks.createDocument).toHaveBeenCalledWith(
          { title: "Test", content: "Content", tags: [] },
          expect.objectContaining({ onSuccess: expect.any(Function) }),
        );
      });

      it("Then the view should return to the list", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        await user.click(screen.getByTestId("form-submit"));

        expect(screen.getByTestId("document-list")).toBeInTheDocument();
      });
    });

    describe("When upload completes", () => {
      it("Then the view should return to the list", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("upload-new-btn"));
        await user.click(screen.getByTestId("upload-complete"));

        expect(screen.getByTestId("document-list")).toBeInTheDocument();
      });
    });

    describe("When the form is cancelled", () => {
      it("Then the view should return to the list", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        await user.click(screen.getByTestId("form-cancel"));

        expect(screen.getByTestId("document-list")).toBeInTheDocument();
      });

      it("Then no new document should be added", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        await user.click(screen.getByTestId("form-cancel"));

        expect(screen.getByTestId("document-count")).toHaveTextContent("2");
      });
    });

    describe("When the container layout is rendered", () => {
      it("Then it should have padding", () => {
        render(<KnowledgeBaseInterface />);
        expect(screen.getByTestId("container")).toHaveClass("py-8");
      });
    });
  });
});
