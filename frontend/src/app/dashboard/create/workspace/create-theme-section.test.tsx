import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import { INITIAL_CREATE_FORM_STATE } from "@/app/dashboard/create/types";
import { LIGHT_THEME_IMAGE_PRESET } from "@/constants/create";
import type { ThemeOption } from "@/app/dashboard/create/theme-options";
import { CreateThemeSection } from "./create-theme-section";

/**
 * Gherkin: tests/features/palette_crud_api.feature and palette-drift-gate.feature
 * (the dropdown renders the dynamic catalog; light palettes still nudge the
 * flat-editorial preset, driven by each option's API mode).
 */
const THEME_OPTIONS: ThemeOption[] = [
  { value: "auto", label: "Auto-detect", mode: null },
  { value: "plasma_magenta", label: "Plasma Magenta", mode: "dark" },
  { value: "paper_editorial", label: "Paper Editorial", mode: "light" },
  { value: "clinical_mint", label: "Clinical Mint", mode: "light" },
];

describe("CreateThemeSection", () => {
  it("renders the catalog themes as options", () => {
    render(
      <CreateThemeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={vi.fn()}
        themeOptions={THEME_OPTIONS}
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
        form={{
          ...INITIAL_CREATE_FORM_STATE,
          imagePreset: "openai__comic_neon",
        }}
        onChange={onChange}
        themeOptions={THEME_OPTIONS}
      />,
    );
    const themeSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(themeSelect!, { target: { value: "paper_editorial" } });
    expect(onChange).toHaveBeenCalledWith({
      theme: "paper_editorial",
      imagePreset: LIGHT_THEME_IMAGE_PRESET,
    });
  });

  it("does not override the preset for a dark theme", () => {
    const onChange = vi.fn();
    render(
      <CreateThemeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={onChange}
        themeOptions={THEME_OPTIONS}
      />,
    );
    const themeSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(themeSelect!, { target: { value: "plasma_magenta" } });
    expect(onChange).toHaveBeenCalledWith({ theme: "plasma_magenta" });
  });

  it("does not patch the preset when it is already flat editorial", () => {
    const onChange = vi.fn();
    render(
      <CreateThemeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={onChange}
        themeOptions={THEME_OPTIONS}
      />,
    );
    const themeSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(themeSelect!, { target: { value: "paper_editorial" } });
    expect(onChange).toHaveBeenCalledWith({ theme: "paper_editorial" });
  });

  it("shows the light-theme hint when a light theme is active", () => {
    render(
      <CreateThemeSection
        form={{ ...INITIAL_CREATE_FORM_STATE, theme: "clinical_mint" }}
        onChange={vi.fn()}
        themeOptions={THEME_OPTIONS}
      />,
    );
    expect(screen.getByRole("note")).toHaveTextContent(/Flat Editorial/);
  });
});
