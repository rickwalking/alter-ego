import { describe, expect, it } from "vitest";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";

describe("create namespace i18n", () => {
  it("defines publishCta in en and pt locales", () => {
    expect(en.create.publishCta).toBe("Open Publish");
    expect(pt.create.publishCta).toBe("Abrir Publicação");
  });

  it("defines the generation log in en and pt locales", () => {
    expect(en.create.generationLog.title).toBe("Generation log");
    expect(pt.create.generationLog.title).toBe("Registro de geração");
    expect(pt.create.generationLog.empty).toBe(
      "Nenhum evento de geração ainda.",
    );
    const byLocale = (left: string, right: string) => left.localeCompare(right);
    const sections = [
      "events",
      "kinds",
      "statuses",
      "outcomes",
      "phases",
      "details",
    ] as const;
    for (const section of sections) {
      expect(
        Object.keys(en.create.generationLog[section]).sort(byLocale),
      ).toEqual(Object.keys(pt.create.generationLog[section]).sort(byLocale));
    }
  });
});
