import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import { INITIAL_CREATE_FORM_STATE } from "@/app/dashboard/create/types";
import { FLAT_EDITORIAL_PRESET } from "@/constants/create";
import { CreateThemeSection } from "./create-theme-section";

// Gherkin: tests/features/image_generation_provider.feature
// (light palettes are explicit-select and pair with the flat-editorial preset).
describe("CreateThemeSection", () => {
  it("lists the new dark and light themes as options", () => {
    render(
      <CreateThemeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("option", { name: /Plasma Magenta/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /Paper Editorial/ }),
    ).toBeInTheDocument();
  });

  it("nudges to the flat-editorial preset when a light theme is selected", () => {
    const onChange = vi.fn();
    render(
      <CreateThemeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={onChange}
      />,
    );
    const themeSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(themeSelect, { target: { value: "paper_editorial" } });
    expect(onChange).toHaveBeenCalledWith({
      theme: "paper_editorial",
      imagePreset: FLAT_EDITORIAL_PRESET,
    });
  });

  it("does not override the preset for a dark theme", () => {
    const onChange = vi.fn();
    render(
      <CreateThemeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={onChange}
      />,
    );
    const themeSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(themeSelect, { target: { value: "plasma_magenta" } });
    expect(onChange).toHaveBeenCalledWith({ theme: "plasma_magenta" });
  });

  it("shows the light-theme hint when a light theme is active", () => {
    render(
      <CreateThemeSection
        form={{ ...INITIAL_CREATE_FORM_STATE, theme: "clinical_mint" }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("note")).toHaveTextContent(/Flat Editorial/);
  });
});
