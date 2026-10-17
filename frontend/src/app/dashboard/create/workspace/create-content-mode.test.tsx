import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import { INITIAL_CREATE_FORM_STATE } from "@/app/dashboard/create/types";
import { CreateModeSection } from "./create-mode-section";
import { CreatePovSection } from "./create-pov-section";
import { CreateTemplateSection } from "./create-template-section";

// Gherkin: tests/features/create-content-mode.feature (AE-0373)
const POV_FORM = { ...INITIAL_CREATE_FORM_STATE, contentMode: "pov" as const };
const PERSONAS = [{ id: "p-1", name: "Pedro" }];

describe("CreateModeSection", () => {
  it("selects Radar IA by default", () => {
    render(
      <CreateModeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={vi.fn()}
        personas={PERSONAS}
      />,
    );
    expect(screen.getByRole("radio", { name: /Radar IA/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(
      screen.getByRole("radio", { name: /Ponto de Vista/ }),
    ).toHaveAttribute("aria-checked", "false");
  });

  it("switches to Ponto de Vista and resets the template", () => {
    const onChange = vi.fn();
    render(
      <CreateModeSection
        form={{ ...INITIAL_CREATE_FORM_STATE, selectedTemplate: 4 }}
        onChange={onChange}
        personas={PERSONAS}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: /Ponto de Vista/ }));
    expect(onChange).toHaveBeenCalledWith({
      contentMode: "pov",
      selectedTemplate: 0,
      imagePreset: "openai__pov_editorial",
    });
  });

  it("switches back to Radar IA with the default preset (AE-0376)", () => {
    const onChange = vi.fn();
    render(
      <CreateModeSection
        form={POV_FORM}
        onChange={onChange}
        personas={PERSONAS}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: /Radar IA/ }));
    expect(onChange).toHaveBeenCalledWith({
      contentMode: "news_analysis",
      selectedTemplate: 0,
      imagePreset: "openai__flat_editorial",
    });
  });

  // Scenario: The owner picks "POV: News" (AE-0406)
  it("switches to POV: News with the POV preset", () => {
    const onChange = vi.fn();
    render(
      <CreateModeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={onChange}
        personas={PERSONAS}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: /POV: News/ }));
    expect(onChange).toHaveBeenCalledWith({
      contentMode: "pov_news",
      selectedTemplate: 0,
      imagePreset: "openai__pov_editorial",
    });
  });

  it("lists the personas with a no-persona option", () => {
    const onChange = vi.fn();
    render(
      <CreateModeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={onChange}
        personas={PERSONAS}
      />,
    );
    const select = screen.getByLabelText(/Persona/);
    expect(
      screen.getByRole("option", { name: "No persona" }),
    ).toBeInTheDocument();
    fireEvent.change(select, { target: { value: "p-1" } });
    expect(onChange).toHaveBeenCalledWith({ personaId: "p-1" });
  });
});

describe("CreatePovSection", () => {
  it("shows the thesis-required note while the thesis is blank", () => {
    render(<CreatePovSection form={POV_FORM} onChange={vi.fn()} />);
    expect(screen.getByRole("note")).toHaveTextContent(/thesis is required/);
  });

  it("hides the note once there is a thesis", () => {
    render(
      <CreatePovSection
        form={{ ...POV_FORM, povThesis: "Minha tese" }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("edits thesis, proof, slide count and CTA goal", () => {
    const onChange = vi.fn();
    render(<CreatePovSection form={POV_FORM} onChange={onChange} />);
    fireEvent.change(screen.getByPlaceholderText(/AI writes the code/), {
      target: { value: "Tese" },
    });
    expect(onChange).toHaveBeenCalledWith({ povThesis: "Tese" });
    fireEvent.change(screen.getByPlaceholderText(/real situation/), {
      target: { value: "Prova" },
    });
    expect(onChange).toHaveBeenCalledWith({ povPersonalProof: "Prova" });
    fireEvent.change(screen.getByLabelText(/Number of slides/), {
      target: { value: "10" },
    });
    expect(onChange).toHaveBeenCalledWith({ slideCount: 10 });
    fireEvent.change(screen.getByLabelText(/Call to action/), {
      target: { value: "send" },
    });
    expect(onChange).toHaveBeenCalledWith({ ctaGoal: "send" });
  });

  it("offers 8, 9 and 10 slides", () => {
    render(<CreatePovSection form={POV_FORM} onChange={vi.fn()} />);
    for (const count of ["8 slides", "9 slides", "10 slides"]) {
      expect(screen.getByRole("option", { name: count })).toBeInTheDocument();
    }
  });
});

describe("CreateTemplateSection modes", () => {
  it("shows the six Radar IA templates", () => {
    render(
      <CreateTemplateSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={vi.fn()}
      />,
    );
    // AE-0415 (B31): the cards are radios that expose the selection.
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(6);
    expect(radios[0]).toHaveAttribute("aria-checked", "true");
    expect(radios[1]).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText("Analysis")).toBeInTheDocument();
  });

  it("shows only the four POV formats in POV mode", () => {
    const onChange = vi.fn();
    render(<CreateTemplateSection form={POV_FORM} onChange={onChange} />);
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    expect(screen.getByText("Opinion (hot take)")).toBeInTheDocument();
    expect(screen.queryByText("Analysis")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("How I do it"));
    expect(onChange).toHaveBeenCalledWith({ selectedTemplate: 1 });
  });
});
