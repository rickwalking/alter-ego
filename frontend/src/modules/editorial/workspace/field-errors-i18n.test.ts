// Scenario: Every field-error message exists in pt and en
import { describe, expect, it } from "vitest";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { FIELD_ERROR_MESSAGE_CODES } from "./constants";

type Messages = Record<string, unknown>;

function flatKeys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) {
    return [prefix];
  }
  return Object.entries(value as Messages).flatMap(([key, child]) =>
    flatKeys(child, prefix ? `${prefix}.${key}` : key),
  );
}

const enErrors = en.editorialWorkflow.review.fieldErrors;
const ptErrors = pt.editorialWorkflow.review.fieldErrors;

describe("field-error i18n (AE-0403)", () => {
  it("has the same field-error keys in pt and en", () => {
    expect(flatKeys(ptErrors).sort((a, b) => a.localeCompare(b))).toEqual(
      flatKeys(enErrors).sort((a, b) => a.localeCompare(b)),
    );
  });

  it.each([...FIELD_ERROR_MESSAGE_CODES])(
    "translates the %s code in both locales",
    (code) => {
      const enCodes: Record<string, string> = enErrors.codes;
      const ptCodes: Record<string, string> = ptErrors.codes;
      expect(enCodes[code]).toEqual(expect.any(String));
      expect(ptCodes[code]).toEqual(expect.any(String));
    },
  );

  it("keeps the manual-fix and blocking strings in both locales", () => {
    expect(ptErrors.submitManualFixes).toBe("Enviar correções manuais");
    expect(enErrors.submitManualFixes).toBe("Submit manual fixes");
    expect(pt.publish.slideEditor.blockingViolations).toContain(
      "correções manuais",
    );
  });
});
