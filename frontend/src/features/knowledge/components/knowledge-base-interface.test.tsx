import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KnowledgeBaseInterface } from "./knowledge-base-interface";

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
    onSelectDocument,
  }: {
    documents: unknown[];
    onCreateNew: () => void;
    onSelectDocument: (doc: unknown) => void;
  }) => (
    <div data-testid="document-list">
      <div data-testid="document-count">{documents.length}</div>
      <button data-testid="create-new-btn" onClick={onCreateNew}>
        Create New
      </button>
      <button data-testid="select-doc-btn" onClick={() => onSelectDocument(documents[0])}>
        Select Document
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

    describe("When a document is selected for editing", () => {
      it("Then the document form should be displayed in edit mode", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("select-doc-btn"));
        expect(screen.getByTestId("document-form")).toBeInTheDocument();
        expect(screen.getByTestId("form-mode")).toHaveTextContent("edit");
      });

      it("Then the card title should indicate editing a document", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("select-doc-btn"));
        expect(screen.getByTestId("card-title")).toHaveTextContent(/edit document/i);
      });
    });

    describe("When the form is submitted for creating", () => {
      it("Then the new document should be added to the list", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        // Open create form
        await user.click(screen.getByTestId("create-new-btn"));
        
        // Submit form
        await user.click(screen.getByTestId("form-submit"));

        // Should be back to list with new document
        expect(screen.getByTestId("document-count")).toHaveTextContent("3");
      });

      it("Then the view should return to the list", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        await user.click(screen.getByTestId("create-new-btn"));
        await user.click(screen.getByTestId("form-submit"));

        expect(screen.getByTestId("document-list")).toBeInTheDocument();
      });
    });

    describe("When the form is submitted for editing", () => {
      it("Then the document should be updated", async () => {
        const user = userEvent.setup();
        render(<KnowledgeBaseInterface />);

        // Select document to edit
        await user.click(screen.getByTestId("select-doc-btn"));
        
        // Submit form
        await user.click(screen.getByTestId("form-submit"));

        // Should be back to list
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
