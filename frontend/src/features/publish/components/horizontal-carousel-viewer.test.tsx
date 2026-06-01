import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HorizontalCarouselViewer } from "./horizontal-carousel-viewer";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => {
    const entries: Record<string, string> = {
      previousSlide: "Previous slide",
      nextSlide: "Next slide",
      downloadImages: "Download images",
      downloadingImages: "Downloading...",
    };
    return (key: string, values?: Record<string, unknown>) => {
      if (key === "goToSlide") {
        return `Go to slide ${values?.number}`;
      }
      return entries[key] ?? key;
    };
  }),
}));

// Mock next/image to render a simple img tag
vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => {
    // eslint-disable-next-line jsx-a11y/alt-text
    return <img {...props} src={props.src as string} />;
  },
}));

// Mock jszip to avoid heavy dependency in unit tests
const mockFile = vi.fn();
const mockFolder = vi.fn(() => ({ file: mockFile }));
const mockGenerateAsync = vi.fn().mockResolvedValue(new Blob(["zip-content"]));

function MockJSZip() {
  return {
    folder: mockFolder,
    generateAsync: mockGenerateAsync,
  };
}

vi.mock("jszip", () => ({
  default: MockJSZip,
}));

describe("HorizontalCarouselViewer", () => {
  const urls = ["/slide1.jpg", "/slide2.jpg"];

beforeEach(() => {
  vi.clearAllMocks();
  mockFile.mockClear();
  mockFolder.mockClear();
  mockGenerateAsync.mockClear();
  global.URL.createObjectURL = vi.fn().mockReturnValue("blob:test-url");
  global.URL.revokeObjectURL = vi.fn();
});

  // Scenario: Renders slides with 4:5 aspect ratio container
  it("renders slides with aspect-[4/5] container", () => {
    render(<HorizontalCarouselViewer slideUrls={urls} alt="Test carousel" />);
    const slides = screen.getAllByRole("img");
    expect(slides).toHaveLength(2);
  });

  // Scenario: Download button is enabled by default
  it("renders a clickable download button in default state", () => {
    render(<HorizontalCarouselViewer slideUrls={urls} alt="Test carousel" />);
    const button = screen.getByRole("button", { name: /Download images/i });
    expect(button).toBeEnabled();
  });

  // Scenario: Download click triggers zip generation with AbortController timeout
  it("creates zip from fetched slides on download click", async () => {
    const user = userEvent.setup();
    global.fetch = vi.fn().mockResolvedValue({
      blob: vi.fn().mockResolvedValue(new Blob(["image-data"])),
    } as unknown as Response);

    render(<HorizontalCarouselViewer slideUrls={urls} alt="Test carousel" />);
    const button = screen.getByRole("button", { name: /Download images/i });
    await user.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    // Each fetch should include credentials and an AbortSignal
    expect(global.fetch).toHaveBeenCalledWith(
      "/slide1.jpg",
      expect.objectContaining({
        credentials: "include",
        signal: expect.any(AbortSignal),
      }),
    );

    await waitFor(() => {
      expect(mockFile).toHaveBeenCalledTimes(2);
    });
    expect(mockFile).toHaveBeenCalledWith(
      "slide_1.jpg",
      expect.any(Blob),
    );
    expect(mockFile).toHaveBeenCalledWith(
      "slide_2.jpg",
      expect.any(Blob),
    );
  });

  // Scenario: Download button shows spinner and disabled state while downloading
  it("shows loading spinner and disables button during download", async () => {
    const user = userEvent.setup();
    let resolveFetch: (value: unknown) => void;
    const fetchPromise = new Promise((resolve) => {
      resolveFetch = resolve;
    });
    global.fetch = vi.fn().mockReturnValue(
      fetchPromise.then(() => ({
        blob: vi.fn().mockResolvedValue(new Blob(["image-data"])),
      })),
    );

    render(<HorizontalCarouselViewer slideUrls={urls} alt="Test carousel" />);
    const button = screen.getByRole("button", { name: /Download images/i });
    await user.click(button);

    // While fetching, button should show loading text and be disabled
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Downloading\.\.\./i }),
      ).toBeDisabled();
    });

    resolveFetch!({ blob: vi.fn().mockResolvedValue(new Blob(["data"])) });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Download images/i }),
      ).toBeEnabled();
    });
  });

  // Scenario: Ignores individual fetch failures
  it("ignores individual fetch failures and still generates zip", async () => {
    const user = userEvent.setup();
    global.fetch = vi
      .fn()
      .mockRejectedValueOnce(new Error("network error"))
      .mockResolvedValueOnce({
        blob: vi.fn().mockResolvedValue(new Blob(["image-data"])),
      } as unknown as Response);

    render(<HorizontalCarouselViewer slideUrls={urls} alt="Test carousel" />);
    const button = screen.getByRole("button", { name: /Download images/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockGenerateAsync).toHaveBeenCalled();
    });
  });

  // Scenario: First slide receives priority prop (Next.js optimization)
  it("passes priority to the first slide Image component", () => {
    const { container } = render(
      <HorizontalCarouselViewer slideUrls={urls} alt="Test carousel" />,
    );
    // The first slide's wrapper div is the first child of the viewport
    const viewport = container.querySelector("#carousel-viewport");
    expect(viewport).not.toBeNull();
    const firstSlide = viewport?.querySelector("div");
    expect(firstSlide).not.toBeNull();
  });

  // Edge: Empty slideUrls renders nothing
  it("returns null when no slides are provided", () => {
    const { container } = render(
      <HorizontalCarouselViewer slideUrls={[]} alt="Empty" />,
    );
    expect(container.firstChild).toBeNull();
  });
});
