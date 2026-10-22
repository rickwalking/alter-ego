import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ImagePromptReview } from "./image-prompt-review";

const prompts = [
  {
    slide_index: 1,
    title: "AI security hook",
    image_prompt: "Cybersecurity analyst reviewing AI risk dashboard",
    rendered_image_prompt: "Rendered provider prompt with neon blue palette",
    image_model: "openai",
    image_style: "cinematic",
    theme_name: "cybersecurity",
    image_generation_key: "1234567890abcdef",
  },
  {
    slide_index: 2,
    title: "Risk pattern",
    image_prompt: "Layered threat model diagram with clear contrast",
  },
];

describe("ImagePromptReview", () => {
  it("renders one read-only prompt textarea per slide", () => {
    render(<ImagePromptReview prompts={prompts} readOnly />);

    expect(screen.getByText("Slide image prompts")).toBeInTheDocument();
    expect(screen.getByText("2 prompts")).toBeInTheDocument();
    expect(screen.getByText("AI security hook")).toBeInTheDocument();
    expect(screen.getByText("Risk pattern")).toBeInTheDocument();
    expect(screen.getByText("Model: openai")).toBeInTheDocument();
    expect(screen.getByText("Style: cinematic")).toBeInTheDocument();
    expect(screen.getByText("Theme: cybersecurity")).toBeInTheDocument();
    expect(screen.getByText("Key: 1234567890")).toBeInTheDocument();

    const firstPrompt = screen.getByLabelText("Image prompt for slide 1");
    const secondPrompt = screen.getByLabelText("Image prompt for slide 2");
    expect(firstPrompt).toHaveValue(
      "Rendered provider prompt with neon blue palette",
    );
    expect(secondPrompt).toHaveValue(
      "Layered threat model diagram with clear contrast",
    );
    expect(firstPrompt).toHaveAttribute("readonly");
    expect(secondPrompt).toHaveAttribute("readonly");
  });

  it("does not render when no prompts are available", () => {
    const { container } = render(<ImagePromptReview prompts={[]} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("leaves prompt textareas enabled when readOnly is false", () => {
    render(<ImagePromptReview prompts={[prompts[0]!]} readOnly={false} />);

    expect(
      screen.getByLabelText("Image prompt for slide 1"),
    ).not.toHaveAttribute("readonly");
  });

  it("defaults the prompt textareas to read-only", () => {
    render(<ImagePromptReview prompts={[prompts[0]!]} />);

    expect(screen.getByLabelText("Image prompt for slide 1")).toHaveAttribute(
      "readonly",
    );
  });

  it("does not render when the prompts are missing", () => {
    const { container } = render(<ImagePromptReview prompts={undefined} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("names the section after the prompts title", () => {
    render(<ImagePromptReview prompts={prompts} />);

    expect(
      screen.getByRole("region", { name: "Slide image prompts" }),
    ).toBeInTheDocument();
  });

  it("labels each textarea with its slide label", () => {
    render(<ImagePromptReview prompts={prompts} />);

    const textarea = screen.getByLabelText("Slide 2 image prompt");
    expect(textarea).toHaveAttribute("id", "image-prompt-2");
    expect(textarea).toBe(screen.getByLabelText("Image prompt for slide 2"));
  });

  it("renders only the badges of the metadata a prompt carries", () => {
    render(<ImagePromptReview prompts={prompts} />);

    const [firstArticle, secondArticle] = screen.getAllByRole("article");
    expect(
      within(firstArticle!).getAllByText(/^(Model|Style|Theme|Key):/),
    ).toHaveLength(4);
    expect(secondArticle!.querySelectorAll("span")).toHaveLength(1);
    expect(secondArticle!.querySelectorAll("div.flex-wrap")).toHaveLength(1);
  });
});
