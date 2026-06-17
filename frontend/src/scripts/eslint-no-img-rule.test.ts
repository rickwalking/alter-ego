/**
 * AE-0202 rule-fires regression test (dogfoods AE-0180): a raw `<img>` element
 * in production `src` must be an ESLint ERROR (`@next/next/no-img-element`), not a
 * warning. The rule was promoted warn -> error once the last prod `<img>`
 * (image-gen-modal.tsx) migrated to next/image; this test proves the promotion
 * actually fires, so it cannot silently regress to a warning.
 *
 * A probe component is written under a real `src/modules/**` path so it is
 * matched by the flat config + tsconfig project, then linted via the ESLint CLI.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const PROBE_DIR = join(FRONTEND_ROOT, "src", "modules", "__eslint_img_probe__");
const PROBE = join(PROBE_DIR, "probe.tsx");
const NO_IMG_ELEMENT = "@next/next/no-img-element";
const SEVERITY_ERROR = 2;
const ESLINT_SUBPROCESS_TIMEOUT_MS = 60_000;

interface EslintMessage {
  ruleId: string | null;
  severity: number;
}
interface EslintResult {
  messages: EslintMessage[];
}

function lintProbe(): { exitCode: number; results: EslintResult[] } {
  try {
    const out = execFileSync(
      "npx",
      [
        "eslint",
        "--format",
        "json",
        "src/modules/__eslint_img_probe__/probe.tsx",
      ],
      { cwd: FRONTEND_ROOT, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] },
    );
    return { exitCode: 0, results: JSON.parse(out) as EslintResult[] };
  } catch (err) {
    const e = err as { status?: number; stdout?: string };
    return {
      exitCode: e.status ?? 1,
      results: JSON.parse(e.stdout ?? "[]") as EslintResult[],
    };
  }
}

describe("no-img-element is an ESLint error (AE-0202)", () => {
  beforeEach(() => mkdirSync(PROBE_DIR, { recursive: true }));
  afterEach(() => rmSync(PROBE_DIR, { recursive: true, force: true }));

  it(
    "ERRORS on a raw <img> in production src",
    () => {
      writeFileSync(
        PROBE,
        `export function Probe(): React.JSX.Element {\n` +
          `  return <img src="/x.png" alt="x" />;\n}\n`,
      );
      const { exitCode, results } = lintProbe();
      const imgFindings = results
        .flatMap((r) => r.messages)
        .filter((m) => m.ruleId === NO_IMG_ELEMENT);

      expect(exitCode).not.toBe(0);
      expect(imgFindings.length).toBeGreaterThan(0);
      expect(imgFindings.every((m) => m.severity === SEVERITY_ERROR)).toBe(
        true,
      );
    },
    ESLINT_SUBPROCESS_TIMEOUT_MS,
  );
});
