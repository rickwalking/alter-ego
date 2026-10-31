/**
 * The rubric card: translated scale and threshold labels in both locales,
 * every content type and the real weights/default flag from the API, and a
 * header that wraps with 44 px actions on a phone.
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { mapQualityRubricToPanelData } from "@/modules/editorial-operations";
import type { QualityRubric } from "@/modules/quality";
import { RubricPanel } from "./rubric-panel";

vi.unmock("next-intl");

const MESSAGES = { en, pt } as const;
type Locale = keyof typeof MESSAGES;

type Criterion = QualityRubric["criteria"][number];
type CriterionValues = Pick<
  Criterion,
  "id" | "scoring_scale" | "weight" | "min_threshold"
>;

function criterion(values: CriterionValues): Criterion {
  return {
    name: `Criterion ${values.id}`,
    description: "",
    evaluation_method: "ai_auto",
    prompt_template: "Score {content}",
    ...values,
  };
}

function scaled(
  id: string,
  scale: string,
  [weight, threshold]: readonly [number, number],
): Criterion {
  return criterion({
    id,
    scoring_scale: scale,
    weight,
    min_threshold: threshold,
  });
}

const RUBRIC: QualityRubric = {
  id: "r-1",
  name: "Carousel quality",
  description: null,
  criteria: [
    scaled("a", "0-100", [0.4, 0.7]),
    scaled("b", "1-10", [0.35, 0.8]),
    scaled("c", "pass_fail", [0.25, 1]),
    scaled("d", "grade_a_f", [1, 0.6]),
  ],
  applicable_content_types: ["carousel", "blog_post"],
  is_default: true,
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
  version: 1,
};

function renderPanel(
  locale: Locale,
  rubric: QualityRubric = RUBRIC,
): ReturnType<typeof render> {
  return render(
    <NextIntlClientProvider locale={locale} messages={MESSAGES[locale]}>
      <RubricPanel
        rubric={mapQualityRubricToPanelData(rubric)}
        onEdit={vi.fn()}
        onDelete={rubric.is_default ? undefined : vi.fn()}
      />
    </NextIntlClientProvider>,
  );
}

describe("RubricPanel", () => {
  it("is fully translated in Portuguese", () => {
    // Scenario: The rubric list is fully translated
    const { container } = renderPanel("pt");
    const text = container.textContent;

    expect(screen.getAllByText("Atinge o limite")).toHaveLength(4);
    expect(screen.getAllByText("Abaixo do limite")).toHaveLength(4);
    expect(text).not.toMatch(/Meets threshold|Below threshold/);
    expect(screen.getByText("≥ 70% (0–100)")).toBeInTheDocument();
    expect(screen.getByText("≥ 80% (1–10)")).toBeInTheDocument();
    expect(
      screen.getByText("≥ 100% (Aprovado / reprovado)"),
    ).toBeInTheDocument();
    expect(screen.getByText("≥ 60% (Nota A–F)")).toBeInTheDocument();
    expect(text).not.toMatch(/pass_fail|grade_a_f|1-10|0-100/);
    expect(screen.getByText("Peso: 0,35")).toBeInTheDocument();
  });

  it("uses an en dash for scale ranges in English", () => {
    // Scenario: Scale ranges use an en dash
    const { container } = renderPanel("en");
    expect(screen.getByText("≥ 80% (1–10)")).toBeInTheDocument();
    expect(container.querySelector(".rubric-header-row")).toHaveTextContent(
      "Poor (1–2)",
    );
    expect(screen.getByText("≥ 100% (Pass / fail)")).toBeInTheDocument();
  });

  it("shows every content type the rubric applies to", () => {
    // Scenario: The card shows every content type the rubric applies to
    renderPanel("pt");
    expect(screen.getByText("Carrossel")).toBeInTheDocument();
    expect(screen.getByText("Post do blog")).toBeInTheDocument();
  });

  it("shows an unknown stored content type and scale as stored", () => {
    // Scenario: The card shows every content type the rubric applies to
    renderPanel("en", {
      ...RUBRIC,
      applicable_content_types: ["newsletter"],
      criteria: [scaled("x", "stars_5", [0.5, 0.5])],
    });
    expect(screen.getByText("newsletter")).toBeInTheDocument();
    expect(screen.getByText("≥ 50% (stars_5)")).toBeInTheDocument();
  });

  it("shows the real weights and default flag, never made-up ones", () => {
    // Scenario: The card shows only the data the API returns
    const { container } = renderPanel("en");
    for (const weight of ["0.4", "0.35", "0.25", "1"]) {
      expect(screen.getByText(`Weight: ${weight}`)).toBeInTheDocument();
    }
    expect(screen.getByText("Default")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/active|\(default\)/i);
  });

  it("drops the default mark and badges a rubric does not have", () => {
    // Scenario: The card shows only the data the API returns
    renderPanel("en", {
      ...RUBRIC,
      is_default: false,
      applicable_content_types: [],
    });
    expect(screen.queryByText("Default")).not.toBeInTheDocument();
    expect(screen.queryByText("Carousel")).not.toBeInTheDocument();
  });

  it("wraps its header and stacks criteria with 44 px actions on a phone", () => {
    // Scenario: The card fits a 390 px screen with tappable actions
    const { container } = renderPanel("en", { ...RUBRIC, is_default: false });
    const edit = screen.getByRole("button", {
      name: "Edit rubric Carousel quality",
    });
    const remove = screen.getByRole("button", {
      name: "Delete rubric Carousel quality",
    });
    for (const action of [edit, remove]) {
      expect(action).toHaveClass("min-h-11", "min-w-11");
      expect(action.parentElement).toHaveClass("flex-wrap");
    }
    expect(container.querySelector(".rubric-panel-header")).toHaveClass(
      "flex-wrap",
    );
    const rows = container.querySelectorAll(".rubric-criterion");
    expect(rows).toHaveLength(4);
    for (const row of rows) {
      expect(row).toHaveClass("flex-col", "sm:grid");
    }
    expect(container.innerHTML).not.toContain("min-w-[480px]");
    expect(container.querySelector(".rubric-header-row")).toHaveClass(
      "hidden",
      "sm:grid",
    );
  });
});
