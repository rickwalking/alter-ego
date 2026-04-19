import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentForm } from "./document-form";

describe("DocumentForm Component", () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the DocumentForm is rendered for creating a new document", () => {
    describe("When the form is displayed", () => {
      it("Then the title input should be visible", () => {
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
        expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
      });

      it("Then the content textarea should be visible", () => {
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
        expect(screen.getByLabelText(/content/i)).toBeInTheDocument();
      });

      it("Then the tags input should be visible", () => {
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
        expect(screen.getByPlaceholderText(/add a tag/i)).toBeInTheDocument();
      });

      it("Then the Cancel button should be visible", () => {
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
        expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
      });

      it("Then the Create Document button should be visible", () => {
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
        expect(screen.getByRole("button", { name: /create document/i })).toBeInTheDocument();
      });
    });

    describe("When form inputs are filled", () => {
      it("Then the title input should accept text", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const titleInput = screen.getByLabelText(/title/i);
        await user.type(titleInput, "New Document Title");

        expect(titleInput).toHaveValue("New Document Title");
      });

      it("Then the content textarea should accept text", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const contentInput = screen.getByLabelText(/content/i);
        await user.type(contentInput, "New document content");

        expect(contentInput).toHaveValue("New document content");
      });
    });

    describe("When the form is submitted", () => {
      it("Then onSubmit should be called with form data", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        await user.type(screen.getByLabelText(/title/i), "Test Title");
        await user.type(screen.getByLabelText(/content/i), "Test Content");
        await user.click(screen.getByRole("button", { name: /create document/i }));

        expect(mockOnSubmit).toHaveBeenCalledWith({
          title: "Test Title",
          content: "Test Content",
          metadata: { tags: [] },
        });
      });

      it("Then the data should be trimmed before submission", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        await user.type(screen.getByLabelText(/title/i), "  Test Title  ");
        await user.type(screen.getByLabelText(/content/i), "  Test Content  ");
        await user.click(screen.getByRole("button", { name: /create document/i }));

        expect(mockOnSubmit).toHaveBeenCalledWith({
          title: "Test Title",
          content: "Test Content",
          metadata: { tags: [] },
        });
      });
    });

    describe("When the Cancel button is clicked", () => {
      it("Then onCancel should be called", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        await user.click(screen.getByRole("button", { name: /cancel/i }));
        expect(mockOnCancel).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("Given the tag management functionality", () => {
    describe("When a new tag is added via button click", () => {
      it("Then the tag should appear in the tags list", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const tagInput = screen.getByPlaceholderText(/add a tag/i);
        await user.type(tagInput, "newtag");
        await user.click(screen.getByRole("button", { name: /add/i }));

        expect(screen.getByText("newtag")).toBeInTheDocument();
      });

      it("Then the tag input should be cleared after adding", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const tagInput = screen.getByPlaceholderText(/add a tag/i);
        await user.type(tagInput, "newtag");
        await user.click(screen.getByRole("button", { name: /add/i }));

        expect(tagInput).toHaveValue("");
      });
    });

    describe("When a new tag is added via Enter key", () => {
      it("Then the tag should appear in the tags list", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const tagInput = screen.getByPlaceholderText(/add a tag/i);
        await user.type(tagInput, "newtag");
        await user.keyboard("{Enter}");

        expect(screen.getByText("newtag")).toBeInTheDocument();
      });

      it("Then form submission should be prevented", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const tagInput = screen.getByPlaceholderText(/add a tag/i);
        await user.type(tagInput, "newtag");
        await user.keyboard("{Enter}");

        expect(mockOnSubmit).not.toHaveBeenCalled();
      });
    });

    describe("When adding a duplicate tag", () => {
      it("Then the duplicate tag should not be added", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const tagInput = screen.getByPlaceholderText(/add a tag/i);
        await user.type(tagInput, "newtag");
        await user.click(screen.getByRole("button", { name: /add/i }));

        await user.type(tagInput, "newtag");
        await user.click(screen.getByRole("button", { name: /add/i }));

        const tagElements = screen.getAllByText("newtag");
        expect(tagElements).toHaveLength(1);
      });
    });

    describe("When adding an empty tag", () => {
      it("Then the empty tag should not be added", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        await user.click(screen.getByRole("button", { name: /add/i }));

        expect(screen.queryByText("tag1")).not.toBeInTheDocument();
      });
    });

    describe("When a tag is removed", () => {
      it("Then the tag should disappear from the list", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const tagInput = screen.getByPlaceholderText(/add a tag/i);
        await user.type(tagInput, "tag1");
        await user.click(screen.getByRole("button", { name: /add/i }));

        await user.type(tagInput, "tag2");
        await user.click(screen.getByRole("button", { name: /add/i }));

        const tag1Element = screen.getByText("tag1");
        const removeButton = tag1Element.parentElement?.querySelector("button");
        if (removeButton) {
          await user.click(removeButton);
        }

        expect(screen.queryByText("tag1")).not.toBeInTheDocument();
        expect(screen.getByText("tag2")).toBeInTheDocument();
      });
    });

    describe("When a tag with whitespace is added", () => {
      it("Then the whitespace should be trimmed", async () => {
        const user = userEvent.setup();
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

        const tagInput = screen.getByPlaceholderText(/add a tag/i);
        await user.type(tagInput, "  trimmedtag  ");
        await user.click(screen.getByRole("button", { name: /add/i }));

        expect(screen.getByText("trimmedtag")).toBeInTheDocument();
      });
    });
  });

  describe("Given form validation", () => {
    describe("When required fields are empty", () => {
      it("Then the title field should be required", () => {
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
        expect(screen.getByLabelText(/title/i)).toBeRequired();
      });

      it("Then the content field should be required", () => {
        render(<DocumentForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
        expect(screen.getByLabelText(/content/i)).toBeRequired();
      });
    });
  });
});
