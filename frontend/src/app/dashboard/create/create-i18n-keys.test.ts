import { describe, expect, it } from "vitest";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";

describe("create namespace i18n", () => {
  it("defines publishCta in en and pt locales", () => {
    expect(en.create.publishCta).toBe("Open Publish");
    expect(pt.create.publishCta).toBe("Abrir Publicação");
  });
});
