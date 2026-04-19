import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentList } from "./document-list";
import type { Document } from "@/schemas/knowledge";

vi.mock("./document-card", () => ({
  DocumentCard: ({
    document,
    onDelete,
  }: {
    document: Document;
    onDelete: () => void;
  }) => (
    <div
      data-testid={`document-card-${document.id}`}
      onClick={onDelete}
      role="button"
    >
      {document.title}
    </div>
  ),
}));

describe("DocumentList Component", () => {
  const mockDocuments: Document[] = [
    {
      id: "1",
      title: "React Guide",
      status: "completed",
      chunk_count: 10,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: { tags: ["react", "frontend"] },
    },
    {
      id: "2",
      title: "TypeScript Basics",
      status: "completed",
      chunk_count: 8,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: { tags: ["typescript", "javascript"] },
    },
    {
      id: "3",
      title: "Node.js Tutorial",
      status: "processing",
      chunk_count: 12,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: { tags: ["nodejs", "backend"] },
    },
  ];

  const mockOnCreateNew = vi.fn();
  const mockOnUploadNew = vi.fn();
  const mockOnDeleteDocument = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the DocumentList is rendered", () => {
    describe("When the list is displayed with documents", () => {
      it("Then all documents should be rendered", () => {
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );
        expect(screen.getByTestId("document-card-1")).toBeInTheDocument();
        expect(screen.getByTestId("document-card-2")).toBeInTheDocument();
        expect(screen.getByTestId("document-card-3")).toBeInTheDocument();
      });

      it("Then the Add Document button should be visible", () => {
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );
        expect(screen.getByRole("button", { name: /new document/i })).toBeInTheDocument();
      });

      it("Then the search input should be visible", () => {
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );
        expect(screen.getByPlaceholderText(/search documents/i)).toBeInTheDocument();
      });
    });

    describe("When the Add Document button is clicked", () => {
      it("Then onCreateNew should be called", async () => {
        const user = userEvent.setup();
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );

        await user.click(screen.getByRole("button", { name: /new document/i }));
        expect(mockOnCreateNew).toHaveBeenCalledTimes(1);
      });
    });

    describe("When searching for documents", () => {
      it("Then documents matching the title should be displayed", async () => {
        const user = userEvent.setup();
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );

        const searchInput = screen.getByPlaceholderText(/search documents/i);
        await user.type(searchInput, "React");

        expect(screen.getByTestId("document-card-1")).toBeInTheDocument();
        expect(screen.queryByTestId("document-card-2")).not.toBeInTheDocument();
        expect(screen.queryByTestId("document-card-3")).not.toBeInTheDocument();
      });

      it("Then documents matching the tags should be displayed", async () => {
        const user = userEvent.setup();
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );

        const searchInput = screen.getByPlaceholderText(/search documents/i);
        await user.type(searchInput, "typescript");

        expect(screen.queryByTestId("document-card-1")).not.toBeInTheDocument();
        expect(screen.getByTestId("document-card-2")).toBeInTheDocument();
        expect(screen.queryByTestId("document-card-3")).not.toBeInTheDocument();
      });

      it("Then case-insensitive search should work", async () => {
        const user = userEvent.setup();
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );

        const searchInput = screen.getByPlaceholderText(/search documents/i);
        await user.type(searchInput, "REACT");

        expect(screen.getByTestId("document-card-1")).toBeInTheDocument();
      });

      it("Then empty search should show all documents", async () => {
        const user = userEvent.setup();
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );

        const searchInput = screen.getByPlaceholderText(/search documents/i);
        await user.type(searchInput, "React");
        await user.clear(searchInput);

        expect(screen.getByTestId("document-card-1")).toBeInTheDocument();
        expect(screen.getByTestId("document-card-2")).toBeInTheDocument();
        expect(screen.getByTestId("document-card-3")).toBeInTheDocument();
      });
    });

    describe("When no documents match the search", () => {
      it("Then a 'no results' message should be displayed", async () => {
        const user = userEvent.setup();
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );

        const searchInput = screen.getByPlaceholderText(/search documents/i);
        await user.type(searchInput, "nonexistent");

        expect(screen.getByText(/no documents found/i)).toBeInTheDocument();
      });
    });

    describe("When there are no documents", () => {
      it("Then an empty state message should be displayed", () => {
        render(
          <DocumentList
            documents={[]}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );
        expect(screen.getByText(/no documents yet/i)).toBeInTheDocument();
      });
    });

    describe("When the search has a search icon", () => {
      it("Then the search input should have left padding", () => {
        render(
          <DocumentList
            documents={mockDocuments}
            onCreateNew={mockOnCreateNew}
            onUploadNew={mockOnUploadNew}
            onDeleteDocument={mockOnDeleteDocument}
          />
        );
        const searchInput = screen.getByPlaceholderText(/search documents/i);
        expect(searchInput).toHaveClass("pl-10");
      });
    });
  });
});
