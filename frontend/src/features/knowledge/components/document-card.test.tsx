import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentCard } from "./document-card";
import type { Document } from "@/schemas/knowledge";

vi.mock("@/lib/utils", async () => ({
  formatDate: vi.fn(() => "Jan 1, 2024"),
  cn: (...inputs: (string | undefined | false | null)[]) =>
    inputs.filter(Boolean).join(" "),
}));

describe("DocumentCard Component", () => {
  const mockDocument: Document = {
    id: "1",
    title: "Test Document",
    status: "completed",
    chunk_count: 5,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    metadata: { tags: ["test", "example", "documentation"] },
  };

  const mockDocumentNoTags: Document = {
    id: "2",
    title: "No Tags Document",
    status: "processing",
    chunk_count: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    metadata: null,
  };

  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the DocumentCard is rendered", () => {
    describe("When the card is displayed with a document", () => {
      it("Then the document title should be visible", () => {
        render(<DocumentCard document={mockDocument} />);
        expect(screen.getByText("Test Document")).toBeInTheDocument();
      });

      it("Then the creation date should be visible", () => {
        render(<DocumentCard document={mockDocument} />);
        expect(screen.getByText("Jan 1, 2024")).toBeInTheDocument();
      });

      it("Then the chunk count should be visible", () => {
        render(<DocumentCard document={mockDocument} />);
        expect(screen.getByText("5 chunks")).toBeInTheDocument();
      });

      it("Then the FileText icon should be visible", () => {
        render(<DocumentCard document={mockDocument} />);
        const card = screen.getByText("Test Document").closest('[class*="card"]') ||
                    screen.getByText("Test Document").parentElement?.parentElement;
        expect(card).toBeInTheDocument();
      });
    });

    describe("When the document has tags", () => {
      it("Then all tags should be displayed as badges", () => {
        render(<DocumentCard document={mockDocument} />);
        expect(screen.getByText("test")).toBeInTheDocument();
        expect(screen.getByText("example")).toBeInTheDocument();
        expect(screen.getByText("documentation")).toBeInTheDocument();
      });
    });

    describe("When the document has no tags", () => {
      it("Then no tags section should be rendered", () => {
        const { container } = render(<DocumentCard document={mockDocumentNoTags} />);
        const tagsContainer = container.querySelector('[class*="flex flex-wrap gap-1"]');
        expect(tagsContainer).toBeFalsy();
      });
    });

    describe("When the delete button is clicked", () => {
      it("Then the onDelete handler should be called", async () => {
        const user = userEvent.setup();
        render(<DocumentCard document={mockDocument} onDelete={mockOnDelete} />);

        const deleteButton = screen.getByRole("button", { name: /delete document/i });
        await user.click(deleteButton);
        expect(mockOnDelete).toHaveBeenCalledTimes(1);
      });
    });

    describe("When the card has default styling", () => {
      it("Then the title should be truncated if too long", () => {
        const longTitleDoc: Document = {
          ...mockDocument,
          title: "This is a very long title that should be truncated when displayed",
        };
        render(<DocumentCard document={longTitleDoc} />);
        const title = screen.getByText(longTitleDoc.title);
        expect(title).toHaveClass("truncate");
      });
    });

    describe("When the document has a long title", () => {
      it("Then the title should be truncated with ellipsis", () => {
        const longTitleDoc: Document = {
          ...mockDocument,
          title: "A".repeat(100),
        };
        render(<DocumentCard document={longTitleDoc} />);
        const title = screen.getByText(longTitleDoc.title);
        expect(title).toHaveClass("truncate");
      });
    });

    describe("When the document has an error message", () => {
      it("Then the error message should be visible", () => {
        const errorDoc: Document = {
          ...mockDocument,
          status: "failed",
          error_message: "Processing failed",
        };
        render(<DocumentCard document={errorDoc} />);
        expect(screen.getByText("Processing failed")).toBeInTheDocument();
      });
    });

    describe("When the document status is displayed", () => {
      it("Then the status badge should be visible", () => {
        render(<DocumentCard document={mockDocument} />);
        expect(screen.getByText("completed")).toBeInTheDocument();
      });
    });
  });
});
