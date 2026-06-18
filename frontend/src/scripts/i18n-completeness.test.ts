/**
 * AE-0214: the i18n-completeness static check — every statically referenced
 * translation key (`useTranslations("ns")` + `t("key")`) must exist in EVERY
 * locale. Passes on the real tree; ERRORS on a seeded referenced-but-missing
 * key.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const SCRIPT = join(FRONTEND_ROOT, "scripts", "check-i18n-completeness.mjs");

function run(env: Record<string, string> = {}): {
  status: number;
  output: string;
} {
  try {
    const output = execFileSync("node", [SCRIPT], {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      env: { ...process.env, ...env },
      stdio: ["pipe", "pipe", "pipe"],
    });
    return { status: 0, output };
  } catch (err) {
    const e = err as { status?: number; stdout?: string; stderr?: string };
    return {
      status: e.status ?? 1,
      output: `${e.stdout ?? ""}${e.stderr ?? ""}`,
    };
  }
}

function seedLocales(
  dir: string,
  keys: Record<string, Record<string, unknown>>,
) {
  const localesDir = join(dir, "locales");
  mkdirSync(localesDir, { recursive: true });
  for (const [locale, messages] of Object.entries(keys)) {
    writeFileSync(join(localesDir, `${locale}.json`), JSON.stringify(messages));
  }
  return localesDir;
}

describe("i18n-completeness static check (AE-0214)", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "i18n-completeness-"));
  });
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it("passes on the real source tree (every referenced key exists in en + pt)", () => {
    const { status, output } = run();
    expect(status, output).toBe(0);
    expect(output).toContain("i18n completeness OK");
  });

  it("FAILS when a referenced key is missing from a locale", () => {
    const src = join(dir, "src");
    mkdirSync(src);
    writeFileSync(
      join(src, "comp.tsx"),
      `const t = useTranslations("create");\nexport function C(){ return t("preview.previousSlide"); }\n`,
    );
    const localesDir = seedLocales(dir, {
      en: { create: { preview: { previousSlide: "Previous" } } },
      pt: { create: { preview: { viewBlog: "Ver" } } }, // missing previousSlide
    });
    const { status, output } = run({
      I18N_SCAN_ROOT: src,
      I18N_LOCALES_DIR: localesDir,
    });
    expect(status, output).not.toBe(0);
    expect(output).toContain("create.preview.previousSlide");
    expect(output).toContain("missing in [pt]");
  });

  it("passes when the referenced key exists in every locale", () => {
    const src = join(dir, "src");
    mkdirSync(src);
    writeFileSync(
      join(src, "comp.tsx"),
      `const t = useTranslations("create");\nexport function C(){ return t("preview.nextSlide"); }\n`,
    );
    const localesDir = seedLocales(dir, {
      en: { create: { preview: { nextSlide: "Next" } } },
      pt: { create: { preview: { nextSlide: "Próximo" } } },
    });
    const { status, output } = run({
      I18N_SCAN_ROOT: src,
      I18N_LOCALES_DIR: localesDir,
    });
    expect(status, output).toBe(0);
    expect(output).toContain("i18n completeness OK");
  });

  it("skips dynamic keys (template literals are not statically resolvable)", () => {
    const src = join(dir, "src");
    mkdirSync(src);
    writeFileSync(
      join(src, "dyn.tsx"),
      'const t = useTranslations("create");\nexport function C(p: string){ return t(`progress.${p}`); }\n',
    );
    const localesDir = seedLocales(dir, {
      en: { create: { other: "x" } },
      pt: { create: { other: "x" } },
    });
    const { status, output } = run({
      I18N_SCAN_ROOT: src,
      I18N_LOCALES_DIR: localesDir,
    });
    expect(status, output).toBe(0);
  });

  it("honors the allow-list for an intentionally exempt key", () => {
    const src = join(dir, "src");
    mkdirSync(src);
    writeFileSync(
      join(src, "comp.tsx"),
      `const t = useTranslations("create");\nexport function C(){ return t("dynamic.case"); }\n`,
    );
    const localesDir = seedLocales(dir, {
      en: { create: { other: "x" } },
      pt: { create: { other: "x" } },
    });
    const allowlist = join(dir, "allow.json");
    writeFileSync(
      allowlist,
      JSON.stringify({ allow: { "create.dynamic.case": "test exemption" } }),
    );
    const { status, output } = run({
      I18N_SCAN_ROOT: src,
      I18N_LOCALES_DIR: localesDir,
      I18N_ALLOWLIST: allowlist,
    });
    expect(status, output).toBe(0);
  });

  it('resolves aliased hooks (const tc = useTranslations("common"))', () => {
    const src = join(dir, "src");
    mkdirSync(src);
    writeFileSync(
      join(src, "alias.tsx"),
      `const tc = useTranslations("common");\nexport function C(){ return tc("missingKey"); }\n`,
    );
    const localesDir = seedLocales(dir, {
      en: { common: { present: "x" } },
      pt: { common: { present: "x" } },
    });
    const { status, output } = run({
      I18N_SCAN_ROOT: src,
      I18N_LOCALES_DIR: localesDir,
    });
    expect(status, output).not.toBe(0);
    expect(output).toContain("common.missingKey");
  });
});
