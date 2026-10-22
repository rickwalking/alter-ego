import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  BLOG_POST_ERR_SLUG_CONFLICT,
  BlogPostMutationError,
} from "@/modules/publishing";
import { NewBlogPostAction } from "./new-blog-post-modal";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const create = vi.fn();

beforeEach(() => {
  push.mockReset();
  create.mockReset();
});

function openForm(): void {
  render(<NewBlogPostAction create={create} />);
  fireEvent.click(screen.getByRole("button", { name: "New Post" }));
}

describe("NewBlogPostAction", () => {
  // Scenario: Clicking New Post opens a form and creates nothing
  it("opens a title form without creating anything", () => {
    openForm();
    expect(screen.getByText("Create New Blog Post")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  // Scenario: Submitting the form creates the draft and opens the editor
  it("creates the draft with the typed title and opens the editor", async () => {
    create.mockResolvedValue({ id: "new-1" });
    openForm();
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "  Agentes e o bug copiado  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/dashboard/blog-posts/new-1/edit"),
    );
    expect(create).toHaveBeenCalledTimes(1);
    expect(create).toHaveBeenCalledWith({
      title: "Agentes e o bug copiado",
      content: { body: "" },
      excerpt: "",
    });
  });

  // Scenario: The form cannot be submitted without a title
  it.each([[""], ["   "]])("disables Create for the title %j", (title) => {
    openForm();
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: title },
    });
    expect(screen.getByRole("button", { name: "Create" })).toBeDisabled();
    expect(create).not.toHaveBeenCalled();
  });

  // Scenario: The title field is focused when the form opens
  it("focuses the title field on open", () => {
    openForm();
    expect(screen.getByLabelText("Title")).toHaveFocus();
  });

  // Scenario: Pressing Enter in the title field creates the draft
  it("creates the draft when Enter is pressed in the title field", async () => {
    create.mockResolvedValue({ id: "new-2" });
    openForm();
    await userEvent.type(
      screen.getByLabelText("Title"),
      "Post via Enter{Enter}",
    );
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/dashboard/blog-posts/new-2/edit"),
    );
    expect(create).toHaveBeenCalledTimes(1);
    expect(create).toHaveBeenCalledWith({
      title: "Post via Enter",
      content: { body: "" },
      excerpt: "",
    });
  });

  // Scenario: The form cannot be submitted without a title
  it("ignores Enter while the title is blank", async () => {
    openForm();
    await userEvent.type(screen.getByLabelText("Title"), "   {Enter}");
    expect(create).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
  });

  // Scenario: Cancelling the form creates nothing
  it("closes on Cancel without creating", () => {
    openForm();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  // Scenario: A failed create keeps the form open with the error
  // Scenario: Creating a post that fails shows an error
  it.each([
    [new Error("boom"), "Could not create the post. Try again."],
    [new BlogPostMutationError(BLOG_POST_ERR_SLUG_CONFLICT), null],
  ])("keeps the form open and shows the error for %s", async (error, text) => {
    create.mockRejectedValue(error);
    openForm();
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Post" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    const alert = await screen.findByRole("alert");
    if (text) expect(alert).toHaveTextContent(text);
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create" })).toBeEnabled();
    expect(push).not.toHaveBeenCalled();
  });
});
