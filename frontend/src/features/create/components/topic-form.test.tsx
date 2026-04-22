import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TopicForm } from "./topic-form";
import type { CarouselCreateRequest } from "@/schemas/carousel";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => {
    const translations: Record<string, string> = {
      "form.topicLabel": "Topic",
      "form.topicPlaceholder": "Enter carousel topic",
      "form.audienceLabel": "Audience",
      "form.audiencePlaceholder": "Who is this for?",
      "form.nicheLabel": "Niche",
      "form.nichePlaceholder": "e.g. AI/ML",
      "form.themeLabel": "Theme",
      "form.imagePresetLabel": "Image Style",
      "form.imagePresetHelp": "Pick model + style",
      "form.submit": "Generate Carousel",
      "form.submitting": "Generating...",
      "themes.auto": "Auto",
      "themes.cybersecurity": "Cybersecurity",
      "themes.ai_competition": "AI Competition",
      "themes.developer_skills": "Developer Skills",
      "themes.source_code": "Source Code",
      "themes.social_engineering": "Social Engineering",
      "imagePresets.gemini_comic_neon": "Gemini Comic Neon",
      "imagePresets.openai_hyperreal": "OpenAI Hyperreal",
      "imagePresets.openai_cinematic": "OpenAI Cinematic",
      "imagePresets.openai_neo_anime": "OpenAI Neo-Anime",
    };
    return (key: string) => translations[key] ?? key;
  }),
}));

describe("TopicForm Component", () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the TopicForm is rendered", () => {
    describe("When the form is displayed", () => {
      it("Then the topic input should be visible", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/topic/i)).toBeInTheDocument();
      });

      it("Then the audience input should be visible", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/audience/i)).toBeInTheDocument();
      });

      it("Then the niche input should be visible", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/niche/i)).toBeInTheDocument();
      });

      it("Then the theme select should be visible", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/theme/i)).toBeInTheDocument();
      });

      it("Then the submit button should be visible with default text", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(
          screen.getByRole("button", { name: /generate carousel/i })
        ).toBeInTheDocument();
      });
    });

    describe("When the theme select is displayed", () => {
      it("Then it should contain the auto option", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        const select = screen.getByLabelText(/theme/i);
        expect(select).toHaveValue("auto");
      });

      it("Then it should contain the cybersecurity option", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        const select = screen.getByLabelText(/theme/i);
        const options = Array.from(select.querySelectorAll("option")).map(
          (o) => o.value
        );
        expect(options).toContain("cybersecurity");
      });

      it("Then it should contain all six theme options", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        const select = screen.getByLabelText(/theme/i);
        const options = Array.from(select.querySelectorAll("option"));
        expect(options).toHaveLength(6);
      });
    });
  });

  describe("Given a user fills out the form", () => {
    describe("When all fields are filled and submitted", () => {
      it("Then onSubmit should be called with the form data", async () => {
        const user = userEvent.setup();
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);

        await user.type(screen.getByLabelText(/topic/i), "React Testing");
        await user.type(screen.getByLabelText(/audience/i), "Developers");
        await user.type(screen.getByLabelText(/niche/i), "Frontend");
        await user.click(screen.getByRole("button", { name: /generate carousel/i }));

        expect(mockOnSubmit).toHaveBeenCalledWith({
          topic: "React Testing",
          audience: "Developers",
          niche: "Frontend",
          theme: "auto",
          image_model: "gemini",
          image_style: "comic_neon",
        } as CarouselCreateRequest);
      });

      it("Then a non-default theme should be submitted when selected", async () => {
        const user = userEvent.setup();
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);

        await user.type(screen.getByLabelText(/topic/i), "AI Trends");
        await user.type(screen.getByLabelText(/audience/i), "Engineers");
        await user.type(screen.getByLabelText(/niche/i), "AI");
        await user.selectOptions(screen.getByLabelText(/theme/i), "ai_competition");
        await user.click(screen.getByRole("button", { name: /generate carousel/i }));

        expect(mockOnSubmit).toHaveBeenCalledWith({
          topic: "AI Trends",
          audience: "Engineers",
          niche: "AI",
          theme: "ai_competition",
          image_model: "gemini",
          image_style: "comic_neon",
        } as CarouselCreateRequest);
      });

      it("Then picking an OpenAI preset should map to model+style", async () => {
        const user = userEvent.setup();
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);

        await user.type(screen.getByLabelText(/topic/i), "Images 2.0");
        await user.type(screen.getByLabelText(/audience/i), "Designers");
        await user.type(screen.getByLabelText(/niche/i), "AI");
        await user.selectOptions(
          screen.getByLabelText(/image style/i),
          "openai__hyperreal",
        );
        await user.click(screen.getByRole("button", { name: /generate carousel/i }));

        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            image_model: "openai",
            image_style: "hyperreal",
          }),
        );
      });
    });

    describe("When the theme is left at default", () => {
      it("Then the theme should default to auto", async () => {
        const user = userEvent.setup();
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);

        await user.type(screen.getByLabelText(/topic/i), "Test Topic");
        await user.type(screen.getByLabelText(/audience/i), "Test Audience");
        await user.type(screen.getByLabelText(/niche/i), "Test Niche");
        await user.click(screen.getByRole("button", { name: /generate carousel/i }));

        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({ theme: "auto" })
        );
      });
    });
  });

  describe("Given the form is in a pending state", () => {
    describe("When isPending is true", () => {
      it("Then the submit button should be disabled", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={true} />);
        expect(
          screen.getByRole("button", { name: /generating/i })
        ).toBeDisabled();
      });

      it("Then the button text should show submitting state", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={true} />);
        expect(
          screen.getByRole("button", { name: /generating/i })
        ).toBeInTheDocument();
      });

      it("Then the form inputs should still be editable", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={true} />);
        expect(screen.getByLabelText(/topic/i)).not.toBeDisabled();
        expect(screen.getByLabelText(/audience/i)).not.toBeDisabled();
        expect(screen.getByLabelText(/niche/i)).not.toBeDisabled();
      });
    });

    describe("When isPending is false", () => {
      it("Then the submit button should be enabled", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(
          screen.getByRole("button", { name: /generate carousel/i })
        ).not.toBeDisabled();
      });
    });
  });

  describe("Given form validation requirements", () => {
    describe("When checking required fields", () => {
      it("Then the topic field should be required", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/topic/i)).toBeRequired();
      });

      it("Then the audience field should be required", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/audience/i)).toBeRequired();
      });

      it("Then the niche field should be required", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/niche/i)).toBeRequired();
      });

      it("Then the topic field should have a max length of 500", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/topic/i)).toHaveAttribute(
          "maxlength",
          "500"
        );
      });

      it("Then the audience field should have a max length of 500", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/audience/i)).toHaveAttribute(
          "maxlength",
          "500"
        );
      });

      it("Then the niche field should have a max length of 200", () => {
        render(<TopicForm onSubmit={mockOnSubmit} isPending={false} />);
        expect(screen.getByLabelText(/niche/i)).toHaveAttribute(
          "maxlength",
          "200"
        );
      });
    });
  });
});
