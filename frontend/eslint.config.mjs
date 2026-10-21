import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import pluginQuery from "@tanstack/eslint-plugin-query";
import sonarjs from "eslint-plugin-sonarjs";
import tseslint from "typescript-eslint";

/**
 * Severity policy: `error` rules gate the build (the `lint` gate runs `eslint --quiet`,
 * which fails on errors only); `warn` rules are an advisory backlog surfaced on changed files
 * by `lint:changed` (which drops `--quiet`), never blanket-ignored. The remaining `warn`s are
 * the size/complexity rules. Severities only ratchet UP (warn -> error), never down.
 *
 * These type-aware rules were each driven to 0 findings in production `src` and promoted to
 * error (rule-fires test: src/scripts/eslint-strict-type-rules.test.ts); floating promises
 * were fixed by voiding or wrapping async handlers, behavior-preserving only. The test-file
 * block turns no-non-null-assertion back off (`!` is idiomatic for known-present fixtures).
 */
const typeCheckedRules = {
  "@typescript-eslint/no-explicit-any": "error",
  "@typescript-eslint/no-non-null-assertion": "error",
  "@typescript-eslint/no-floating-promises": "error",
  "@typescript-eslint/no-misused-promises": "error",
  "@typescript-eslint/prefer-nullish-coalescing": "error",
  "@typescript-eslint/prefer-optional-chain": "error",
  "@typescript-eslint/no-unnecessary-condition": "error",
};

/** Size/complexity rules tuned by the project block below; the strict presets never touch them. */
const SIZE_RULES = new Set([
  "max-lines-per-function",
  "max-lines",
  "max-statements",
  "complexity",
  "max-depth",
  "sonarjs/cognitive-complexity",
]);

/** Rules whose severity and options the project block below declares itself. */
const PROJECT_OWNED_RULES = new Set([
  "@typescript-eslint/no-unused-vars",
  ...Object.keys(typeCheckedRules),
]);

/**
 * Preset rule options that differ from the preset defaults (severity stays "error").
 * - no-confusing-void-expression `ignoreArrowShorthand`: the idiomatic React handler shorthand
 *   `onClick={() => setOpen(false)}` stays legal; void values in any other position still error.
 * - restrict-template-expressions `allowNumber`: numbers stringify predictably (CSS lengths,
 *   counts, ids); every other non-string type still errors. This matches recommendedTypeChecked.
 */
const PRESET_RULE_OPTIONS = {
  "@typescript-eslint/no-confusing-void-expression": {
    ignoreArrowShorthand: true,
  },
  "@typescript-eslint/restrict-template-expressions": {
    allowAny: false,
    allowBoolean: false,
    allowNever: false,
    allowNullish: false,
    allowNumber: true,
    allowRegExp: false,
  },
};

/** Severity value that disables a rule in a preset. */
const OFF = "off";

/** Severity every enabled preset rule is raised to. */
const ERROR = "error";

/**
 * Raises a preset rule entry to "error", keeping its options; a rule the preset turns off stays off.
 * @param {string} rule
 * @param {unknown} entry
 * @returns {unknown}
 */
function toErrorEntry(rule, entry) {
  const severity = Array.isArray(entry) ? entry[0] : entry;
  if (severity === OFF || severity === 0) return OFF;
  if (rule in PRESET_RULE_OPTIONS) return [ERROR, PRESET_RULE_OPTIONS[rule]];
  return Array.isArray(entry) ? [ERROR, ...entry.slice(1)] : ERROR;
}

/** typescript-eslint strictTypeChecked + stylisticTypeChecked and sonarjs recommended, all at "error". */
const strictPresetRules = Object.fromEntries(
  Object.entries({
    ...Object.assign(
      {},
      ...[
        ...tseslint.configs.strictTypeChecked,
        ...tseslint.configs.stylisticTypeChecked,
      ].map((config) => config.rules ?? {}),
    ),
    ...sonarjs.configs.recommended.rules,
  })
    .filter(([rule]) => !SIZE_RULES.has(rule) && !PROJECT_OWNED_RULES.has(rule))
    .map(([rule, entry]) => [rule, toErrorEntry(rule, entry)]),
);

/**
 * Strict-preset rules relaxed for test files only.
 * - prefer-promise-reject-errors `allowThrowingUnknown`: tests that cover the non-Error rejection
 *   branch reject with a deliberately `unknown`-typed value; literal non-Error rejections still error.
 * - no-hardcoded-passwords: the e2e setup falls back to the seeded test account's well-known
 *   password when PLAYWRIGHT_E2E_PASSWORD is unset; no real credential lives in test code.
 */
const TEST_PRESET_RULE_OVERRIDES = {
  "@typescript-eslint/prefer-promise-reject-errors": [
    ERROR,
    { allowThrowingUnknown: true },
  ],
  "sonarjs/no-hardcoded-passwords": OFF,
};

/**
 * Files whose clear-text URL is a reviewed exception to sonarjs/no-clear-text-protocols:
 * the in-cluster backend URL stays on the private Docker network behind the TLS edge proxy.
 */
const IN_CLUSTER_HTTP_FILES = ["src/constants/api.ts"];

/** Comment markers that must not survive in source. */
const WARNING_COMMENT_TERMS = ["todo", "fixme", "xxx", "hack"];

/**
 * Blocks, in order:
 * - Project rules: the early-return rules (no-else-return, no-lonely-if) are auto-fixable and
 *   error so they gate; max-params enforces the <=3 arguments rule; no-img-element is error
 *   (all production `<img>` use next/image; rule-fires test eslint-no-img-rule.test.ts).
 *   `no-restricted-syntax` holds the single global fetch-in-useEffect guard (rule-fires test
 *   eslint-fetch-rule.test.ts) on purpose: flat config REPLACES that rule per matched file
 *   instead of merging it, so a scoped `warn` would silently downgrade it. Broad raw-fetch
 *   steering needs a separate mechanism (e.g. a ratchet script).
 * - React components: a JSX-calibrated function-size ceiling (150). A render function is
 *   mostly declarative JSX, so the logic limits do not translate, while genuinely huge
 *   components are still flagged. Warnings are enforced on the diff by lint:changed with
 *   --max-warnings=0.
 * - Hooks: no raw `fetch(...)` (route through TanStack Query or the api-client). The selector
 *   matches an Identifier callee named `fetch` only, not `refetch()` nor `window.fetch(...)`.
 *   The global fetch-in-useEffect guard is re-declared here because flat config replaces
 *   `no-restricted-syntax` rather than merging it.
 * - Module boundaries: features/components/lib must not import App Router pages.
 *   Cross-feature internal imports are forbidden by the scripts/check-feature-boundaries.mjs
 *   ratchet (run via `npm run lint`), which grandfathers scripts/feature-boundary-baseline.json
 *   and ratchets the count down, something `no-restricted-imports` cannot do.
 * - No magic numbers in the logic layer (`.ts` in lib/modules/app). HTTP statuses live in
 *   `HTTP_STATUS`, the API base URL in `constants/api`. Excluded: the named-literal layer
 *   (`src/constants/**` and module constants files), Zod bounds in `src/schemas/**` (self-
 *   documenting at the call site), TSX components (design tokens, SVG geometry, timings) and
 *   `route.ts` (Next.js segment config such as `maxDuration` must be a static literal).
 * - Test files: size rules, no-magic-numbers (fixtures use literal statuses/sizes),
 *   no-non-null-assertion and no-img-element (tests mock `next/image` with a plain `<img>`)
 *   are off.
 */
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "eslint.config.mjs",
    "postcss.config.mjs",
    ".stryker-tmp/**",
    "coverage/**",
    "reports/**",
    "scripts/**",
    ".storybook/**",
    "**/*.stories.tsx",
    "**/*.stories.ts",
  ]),
  {
    files: ["**/*.ts", "**/*.tsx"],
    rules: {
      ...strictPresetRules,
      "no-warning-comments": [
        ERROR,
        { terms: WARNING_COMMENT_TERMS, location: "anywhere" },
      ],
    },
  },
  {
    plugins: {
      "@tanstack/query": pluginQuery,
      sonarjs,
    },
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      ...typeCheckedRules,
      "max-lines": [
        "warn",
        { max: 400, skipBlankLines: true, skipComments: true },
      ],
      "max-lines-per-function": [
        "warn",
        { max: 50, skipBlankLines: true, skipComments: true, IIFEs: true },
      ],
      complexity: ["warn", 10],
      "max-depth": ["warn", 4],
      "no-else-return": ["error", { allowElseIf: false }],
      "no-lonely-if": "error",
      "max-params": ["error", 3],
      "max-statements": ["warn", 25],
      "sonarjs/cognitive-complexity": ["warn", 15],
      "@tanstack/query/exhaustive-deps": "error",
      "no-console": ["error", { allow: ["warn", "error"] }],
      "@next/next/no-img-element": "error",
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "CallExpression[callee.name='useEffect'] CallExpression[callee.name='fetch']",
          message:
            "Do not fetch() inside useEffect — use TanStack Query, a Server Component, or authenticated-fetch.",
        },
      ],
    },
  },
  {
    files: ["src/app/**/page.tsx", "src/**/*.tsx"],
    ignores: [
      "src/lib/**/*.tsx",
      "src/**/hooks/**/*.tsx",
      "**/*.test.tsx",
      "**/*.test-utils.tsx",
    ],
    rules: {
      "max-lines": [
        "warn",
        { max: 200, skipBlankLines: true, skipComments: true },
      ],
      "max-lines-per-function": [
        "warn",
        { max: 150, skipBlankLines: true, skipComments: true, IIFEs: true },
      ],
    },
  },
  {
    files: ["src/lib/**/*.ts", "src/features/**/helpers.ts"],
    rules: {
      "max-lines-per-function": ["warn", 30],
      "max-statements": ["warn", 20],
    },
  },
  {
    files: ["src/**/hooks/**/*.ts", "src/**/hooks/**/*.tsx"],
    rules: {
      "max-statements": ["warn", 20],
      complexity: ["warn", 8],
      "no-restricted-syntax": [
        "error",
        {
          selector: "CallExpression > Identifier.callee[name='fetch']",
          message:
            "Hooks must use TanStack Query (or the api-client), not raw fetch.",
        },
        {
          selector:
            "CallExpression[callee.name='useEffect'] CallExpression[callee.name='fetch']",
          message:
            "Do not fetch() inside useEffect — use TanStack Query, a Server Component, or authenticated-fetch.",
        },
      ],
    },
  },
  {
    files: ["src/features/**", "src/components/**", "src/lib/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["**/app/**", "../app/**", "../../app/**"],
              message:
                "Do not import App Router pages from features/components/lib.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: {
      parserOptions: {
        projectService: false,
      },
    },
  },
  {
    files: ["src/lib/**/*.ts", "src/modules/**/*.ts", "src/app/**/*.ts"],
    ignores: [
      "src/constants/**",
      "src/schemas/**",
      "**/constants.ts",
      "**/constants/**",
      "**/route.ts",
      "**/*.test.ts",
      "**/*.test-utils.ts",
    ],
    rules: {
      "no-magic-numbers": [
        "error",
        {
          ignore: [-1, 0, 1, 2, 100],
          ignoreArrayIndexes: true,
          ignoreDefaultValues: true,
          enforceConst: true,
          ignoreEnums: true,
        },
      ],
    },
  },
  {
    files: [
      "**/*.test.ts",
      "**/*.test.tsx",
      "**/*.test-utils.ts",
      "**/*.test-utils.tsx",
      "tests/**",
      "src/test/**",
    ],
    rules: {
      "max-lines-per-function": "off",
      "max-lines": "off",
      complexity: "off",
      "max-statements": "off",
      "sonarjs/cognitive-complexity": "off",
      "no-magic-numbers": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
      "@next/next/no-img-element": "off",
      ...TEST_PRESET_RULE_OVERRIDES,
    },
  },
  {
    files: IN_CLUSTER_HTTP_FILES,
    rules: {
      "sonarjs/no-clear-text-protocols": OFF,
    },
  },
]);
