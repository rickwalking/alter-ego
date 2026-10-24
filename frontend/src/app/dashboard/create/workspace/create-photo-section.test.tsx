import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@/test/utils";
import { CreatePhotoSection } from "./create-photo-section";

/** Gherkin: backend/tests/features/carousel_pov_layouts.feature. */
const PHOTOS = [
  { id: "a1", pose_tag: "Apontando" },
  { id: "b2", pose_tag: null },
];

function renderSection(
  overrides: Partial<Parameters<typeof CreatePhotoSection>[0]> = {},
) {
  const props = {
    photos: PHOTOS,
    selectedId: "a1",
    onSelect: vi.fn(),
    onUpload: vi.fn(),
    uploading: false,
    uploadFailed: false,
    onDelete: vi.fn(),
    deleting: false,
    deleteBlockedBy: null,
    deleteFailed: false,
    ...overrides,
  };
  render(<CreatePhotoSection {...props} />);
  return props;
}

describe("CreatePhotoSection", () => {
  it("marks the selected photo and selects another", () => {
    const props = renderSection();
    expect(screen.getByRole("radio", { name: "Apontando" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    fireEvent.click(screen.getByRole("radio", { name: "Photo" }));
    expect(props.onSelect).toHaveBeenCalledWith("b2");
  });

  it("serves thumbnails from the owner's library", () => {
    renderSection();
    const button = screen.getByRole("radio", { name: "Apontando" });
    const image = button.querySelector("img");
    expect(image?.getAttribute("src")).toContain(
      "/api/carousels/creator-assets/a1/image",
    );
    expect(image?.getAttribute("alt")).toBe("Apontando");
  });

  it("explains the empty library", () => {
    renderSection({ photos: [], selectedId: "" });
    expect(screen.getByRole("note")).toHaveTextContent(/No photos yet/);
  });

  it("uploads a file", () => {
    const props = renderSection();
    const file = new File(["x"], "me.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText(/Upload a new photo/), {
      target: { files: [file] },
    });
    expect(props.onUpload).toHaveBeenCalledWith(file);
  });

  it("shows upload progress and failure", () => {
    renderSection({ uploading: true, uploadFailed: true });
    expect(screen.getByText("Uploading…")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      /could not be uploaded/,
    );
  });

  /** Scenario: Deleting an unused photo after confirming */
  it("deletes the selected photo only after the confirm", () => {
    const props = renderSection();
    fireEvent.click(
      screen.getByRole("button", { name: "Delete selected photo" }),
    );
    expect(props.onDelete).not.toHaveBeenCalled();
    const group = screen.getByRole("group", {
      name: "Delete this photo from the library? It is removed from the server.",
    });
    fireEvent.click(within(group).getByRole("button", { name: "Delete" }));
    expect(props.onDelete).toHaveBeenCalledWith("a1");
    expect(screen.queryByRole("group")).toBeNull();
  });

  /** Scenario: Cancelling the delete keeps the photo */
  it("cancels the delete without calling it", () => {
    const props = renderSection();
    fireEvent.click(
      screen.getByRole("button", { name: "Delete selected photo" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(props.onDelete).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Delete selected photo" }),
    ).toBeInTheDocument();
  });

  /** Scenario: A photo in use lists the carousels that use it */
  it("lists the carousels that block the delete with links", () => {
    renderSection({
      deleteFailed: true,
      deleteBlockedBy: {
        carousels: [
          { id: "c-1", title: "Agentes no trabalho" },
          { id: "c-2", title: null },
        ],
        topics: [],
      },
    });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("This photo is in use");
    expect(
      within(alert).getByRole("link", { name: "Agentes no trabalho" }),
    ).toHaveAttribute("href", "/dashboard/create/c-1");
    expect(
      within(alert).getByRole("link", { name: "Untitled carousel" }),
    ).toHaveAttribute("href", "/dashboard/create/c-2");
    expect(
      screen.queryByText("Could not delete the photo. Try again."),
    ).toBeNull();
  });

  /** Scenario: A photo an autopilot topic uses as its cover lists the topic */
  it("lists the autopilot topics that block the delete", () => {
    renderSection({
      deleteFailed: true,
      deleteBlockedBy: {
        carousels: [],
        topics: [
          { id: "t-1", title: "Agentes no trabalho" },
          { id: null, title: null },
        ],
      },
    });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Autopilot topic: Agentes no trabalho");
    expect(alert).toHaveTextContent(
      "Autopilot topic: cover waiting for a topic",
    );
    expect(within(alert).queryByRole("link")).toBeNull();
  });

  /** Scenario: Deleting an unused photo after confirming */
  it("shows a generic failure and the deleting state", () => {
    renderSection({ deleteFailed: true, deleting: true });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not delete the photo. Try again.",
    );
    expect(
      screen.getByRole("button", { name: /Deleting/ }),
    ).toBeInTheDocument();
  });

  /** Scenario: Cancelling the delete keeps the photo */
  it("offers no delete without a selected library photo", () => {
    renderSection({ selectedId: "gone" });
    expect(
      screen.queryByRole("button", { name: "Delete selected photo" }),
    ).toBeNull();
  });

  /** Scenario: The Slide 1 photo shows curated suggestions for the topic and palette */
  it("renders the cover prompt field under the library", () => {
    renderSection({ promptField: <p>cover prompt slot</p> });
    expect(screen.getByText("cover prompt slot")).toBeInTheDocument();
  });

  it("renders no prompt slot when none is given", () => {
    renderSection();
    expect(screen.queryByText("cover prompt slot")).toBeNull();
  });
});
