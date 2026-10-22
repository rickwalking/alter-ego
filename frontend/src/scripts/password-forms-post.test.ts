/**
 * Every form with a password field is a POST form, so a submit before hydration
 * (or without JavaScript) can never put credentials in a GET URL. Passes on the
 * real tree; fires on a seeded GET-default form.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const SRC_ROOT = join(import.meta.dirname, "..");
const COMPONENT_SUFFIX = ".tsx";
const TEST_SUFFIX = ".test.tsx";
const FORM_TAG = /<form\b[^>]*>/g;
const POST_METHOD = /\bmethod="post"/;
const PASSWORD_FIELD = /\b(?:type|name|id|htmlFor)=\{?[`"'][^`"']*password/i;
const ARROW = /=>/g;

/** Opening `<form>` tags of a source file that do not declare method="post". */
function getDefaultForms(source: string): string[] {
  if (!PASSWORD_FIELD.test(source)) return [];
  const tags = source.replace(ARROW, "").match(FORM_TAG) ?? [];
  return tags.filter((tag) => !POST_METHOD.test(tag));
}

function componentFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return componentFiles(path);
    return name.endsWith(COMPONENT_SUFFIX) && !name.endsWith(TEST_SUFFIX)
      ? [path]
      : [];
  });
}

describe("password forms post", () => {
  // Scenario: Every form with a password field posts
  it("finds no password form left on the default GET", () => {
    const offenders = componentFiles(SRC_ROOT).flatMap((path) =>
      getDefaultForms(readFileSync(path, "utf8")).map(
        (tag) => `${relative(SRC_ROOT, path)}: ${tag}`,
      ),
    );

    expect(offenders).toEqual([]);
  });

  // Scenario: Every form with a password field posts
  it.each([
    [
      '<form onSubmit={submit}><input type="password" name="password" /></form>',
    ],
    ['<form method="get"><input name="password" /></form>'],
    ['<form className="x">\n<input id={`${id}-password`} /></form>'],
    [
      '<form\n  onSubmit={(e) => {\n    void submit(e);\n  }}\n  method="get"\n>\n<input type="password" /></form>',
    ],
  ])("fires on a seeded GET-default form: %s", (source) => {
    expect(getDefaultForms(source)).toHaveLength(1);
  });

  // Scenario: Every form with a password field posts
  it("ignores forms without a password field and POST forms", () => {
    expect(
      getDefaultForms('<form onSubmit={s}><input name="title" /></form>'),
    ).toEqual([]);
    expect(
      getDefaultForms(
        '<form method="post" action="/auth/login"><input type="password" /></form>',
      ),
    ).toEqual([]);
  });
});
