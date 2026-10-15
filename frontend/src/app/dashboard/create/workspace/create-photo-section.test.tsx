import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import { CreatePhotoSection } from "./create-photo-section";

// Gherkin: backend/tests/features/carousel_pov_layouts.feature (AE-0376)
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
});
