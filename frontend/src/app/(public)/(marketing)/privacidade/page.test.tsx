/** Gherkin: frontend/tests/features/public-privacy-page.feature */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import pt from "@/i18n/locales/pt.json";
import {
  generateMetadata,
  loadPolicyTranslators,
  PrivacyPolicyView,
} from "./page";

const requested: string[] = [];

vi.mock("next-intl/server", async () => {
  const { createTranslator } =
    await vi.importActual<typeof import("next-intl")>("next-intl");
  return {
    getTranslations: (
      options: string | { locale: string; namespace: string },
    ) => {
      const namespace =
        typeof options === "string" ? options : options.namespace;
      const locale = typeof options === "string" ? "pt" : options.locale;
      requested.push(locale);
      return Promise.resolve(
        createTranslator({
          locale,
          messages: pt,
          namespace: namespace as "privacy",
        }),
      );
    },
  };
});

async function renderPage(): Promise<HTMLElement> {
  const { container } = render(
    <PrivacyPolicyView {...await loadPolicyTranslators()} />,
  );
  return container;
}

describe("PrivacyPolicyPage", () => {
  // Scenario: The privacy policy renders in Portuguese for every visitor
  it("renders the policy in Portuguese with its sections", async () => {
    requested.length = 0;
    const container = await renderPage();

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Política de Privacidade",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Última atualização: 11/11/2026"),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent),
    ).toEqual([
      "O que é este site",
      "Quais dados são usados",
      "Por quanto tempo",
      "Seus direitos (LGPD)",
    ]);
    expect(container.querySelector("article")).toHaveAttribute("lang", "pt-BR");
    expect(new Set(requested)).toEqual(new Set(["pt"]));
  });

  // Scenario: The privacy policy renders in Portuguese for every visitor
  it("keeps the emphasis and the three data items", async () => {
    await renderPage();

    expect(screen.getByText("minha própria").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByText("Visitas ao site:").tagName).toBe("STRONG");
  });

  // Scenario: The only contact is the LinkedIn profile
  it("offers the LinkedIn profile as the only contact", async () => {
    const container = await renderPage();

    const linkedIn = screen.getByRole("link", { name: "LinkedIn" });
    expect(linkedIn).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/pedro-marins-179971ba",
    );
    const text = container.textContent;
    expect(text).not.toMatch(/@[a-z0-9-]+\.[a-z]/i);
    expect(text).not.toMatch(/CNPJ|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/);
    expect(container.querySelector('a[href^="mailto:"]')).toBeNull();
  });

  // Scenario: The marketing footer links the privacy policy
  it("ends with the marketing footer and its privacy link", async () => {
    await renderPage();

    expect(screen.getByRole("link", { name: "Privacidade" })).toHaveAttribute(
      "href",
      "/privacidade",
    );
  });

  // Scenario: The privacy policy renders in Portuguese for every visitor
  it("titles the page as the privacy policy", async () => {
    const metadata = await generateMetadata();

    expect(metadata.title).toBe("Política de Privacidade · Pedro Marins");
  });
});
