import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import pluginQuery from "@tanstack/eslint-plugin-query";
import sonarjs from "eslint-plugin-sonarjs";

// AE-0166 — severity policy. `error` rules GATE the build (the `lint` gate runs
// `eslint --quiet`, which fails on errors only). `warn` rules are advisory: a
// tracked backlog, SURFACED on changed files by `lint:changed` (which drops
// `--quiet`) as a paydown nudge, but NOT gating — promoting them to a global
// error would require mass refactoring of pre-existing violations (counts
// measured 2026-06-17):
//   no-unnecessary-condition (69), prefer-nullish-coalescing (50),
//   and the size/complexity rules below. They are paid down opportunistically,
//   never blanket-ignored, and the severities only ever ratchet UP (warn→error),
//   never down.
//
// Promoted to error (count driven to 0 in production `src`):
//   no-non-null-assertion (AE-0199), no-floating-promises +
//   no-misused-promises (AE-0200), max-params (AE-0201).
//
// no-img-element (AE-0202): 8 -> 0. All prod `<img>` migrated to next/image,
//   including image-gen-modal.tsx (generated preview uses `fill` in a fixed
//   aspect-ratio container with `object-contain` + `unoptimized`, which is
//   dimension-agnostic). Rule promoted warn -> error; a seeded `<img>` is
//   verified to ERROR by src/scripts/eslint-no-img-rule.test.ts.
const typeCheckedRules = {
  "@typescript-eslint/no-explicit-any": "error",
  // AE-0199: all pre-existing findings were in tests -> production `src` clean,
  // promoted to error. The test-file override below turns it back off (`!` is
  // idiomatic for known-present fixtures in tests).
  "@typescript-eslint/no-non-null-assertion": "error",
  // AE-0200: floating promises voided / async handlers wrapped -> 0 findings,
  // promoted to error (behavior-preserving fixes only).
  "@typescript-eslint/no-floating-promises": "error",
  "@typescript-eslint/no-misused-promises": "error",
  "@typescript-eslint/prefer-nullish-coalescing": "warn",
  // Zero pre-existing violations after AE-0166 cleanup -> promoted to error.
  "@typescript-eslint/prefer-optional-chain": "error",
  "@typescript-eslint/no-unnecessary-condition": "warn",
};

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
      // Early-return / guard-clause enforcement (AE-0147). Both are
      // auto-fixable and behavior-preserving; errors so they gate under
      // `eslint --quiet` (which suppresses warnings).
      "no-else-return": ["error", { allowElseIf: false }],
      "no-lonely-if": "error",
      // AE-0201: refactored 4-arg sites to typed options objects (CLAUDE.md
      // <=3 args) -> 0 findings, promoted to error.
      "max-params": ["error", 3],
      "max-statements": ["warn", 25],
      "sonarjs/cognitive-complexity": ["warn", 15],
      "@tanstack/query/exhaustive-deps": "error",
      // AE-0166: 0 pre-existing violations -> error.
      "no-console": ["error", { allow: ["warn", "error"] }],
      "@next/next/no-img-element": "error",
      // Data-fetching anti-pattern (AE-0166; frontend/CLAUDE.md "NEVER use
      // useEffect for Data Fetching"). fetch-in-useEffect ERRORS everywhere (0
      // pre-existing violations); steer to TanStack Query / a Server Component /
      // authenticated-fetch. A regression test (src/scripts/eslint-fetch-rule.test.ts)
      // proves it fires. NOTE: this is the single global `no-restricted-syntax`
      // rule on purpose — ESLint flat config does NOT merge `no-restricted-syntax`
      // across config objects (a later object's value REPLACES it). A broader
      // raw-fetch `warn` in a scoped block was removed because it silently
      // downgraded THIS error in src/modules + src/components; the stronger guard
      // wins. Broad raw-fetch steering, if wanted, needs a separate mechanism
      // (e.g. a ratchet script), not a colliding `no-restricted-syntax`.
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
    // AE-0185 — JSX-calibrated function-size ceiling for React components.
    // A page/component render function is mostly declarative JSX, not control
    // flow; the logic limits (30 for lib/helpers, the global 50, and the hook
    // limits below) do not translate. 150 keeps a real ceiling — genuinely huge
    // components (e.g. HomePageContent ~1210 lines) are STILL flagged — while no
    // longer punishing legitimate ~41-150 line presentational components.
    files: ["src/app/**/page.tsx", "src/**/*.tsx"],
    ignores: [
      "src/lib/**/*.tsx",
      "src/**/hooks/**/*.tsx",
      "**/*.test.tsx",
      "**/*.test-utils.tsx",
    ],
    rules: {
      // Warn globally; diff-scoped CI (lint:changed) enforces with --max-warnings=0.
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
      // AE-0184 — hooks must not perform raw data fetching: route through
      // TanStack Query (or the shared api-client). The bare-`fetch`
      // CallExpression selector matches `fetch(...)` (Identifier callee named
      // `fetch`) only — it does NOT flag `refetch()` (a different callee name)
      // nor `window.fetch(...)` (MemberExpression callee). NOTE: ESLint flat
      // config REPLACES `no-restricted-syntax` per matched file rather than
      // merging it, so the global fetch-in-useEffect guard is re-declared here
      // to keep it in force for hook files.
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
    // Module-boundary guards.
    //
    // 1. `app/**` guard (below): features/components/lib must not import App
    //    Router pages.
    // 2. Cross-feature INTERNAL imports (`features/A/**` importing
    //    `features/B/**`, B != A) are forbidden by the ratchet in
    //    `scripts/check-feature-boundaries.mjs`, run via `npm run lint`
    //    (and `lint:all`). Existing violations are grandfathered in
    //    `scripts/feature-boundary-baseline.json`; NEW ones fail the build.
    //    The ratchet lives in a script (not `no-restricted-imports`) because it
    //    must grandfather a committed baseline and ratchet the count down — see
    //    AE-0083, mirrors the backend ratchet AE-0082.
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
    // No magic numbers (AE-0145). Error so it gates under `eslint --quiet`.
    // HTTP status codes live in `HTTP_STATUS` and the API base URL in
    // `constants/api`; other recurring literals are extracted to named
    // constants. The rule is scoped to the application *logic* layer (`.ts`
    // in lib / modules / app / hooks). It deliberately excludes:
    //   - `src/constants/**` — the named-literal layer itself (the place the
    //     rule pushes numbers *into*; flagging it is circular);
    //   - `src/schemas/**` — Zod validation bounds (`.max(500)`, `.min(...)`)
    //     are self-documenting at the call site;
    //   - `**/*.tsx` — presentational components, where literals are design
    //     tokens / SVG geometry / animation timings (Tailwind-equivalent).
    // `ignore` keeps the universally-meaningful small set; array indexes /
    // default params are exempt structurally.
    files: ["src/lib/**/*.ts", "src/modules/**/*.ts", "src/app/**/*.ts"],
    ignores: [
      "src/constants/**",
      "src/schemas/**",
      // Module-local constants files are part of the named-literal layer too.
      "**/constants.ts",
      "**/constants/**",
      // Next.js route segment config exports (e.g. `maxDuration`) must be
      // statically-analyzable literals; they cannot reference constants.
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
      // Test fixtures legitimately use literal status codes / sizes.
      "no-magic-numbers": "off",
      // AE-0199: `!` is idiomatic in tests for known-present fixtures; the rule
      // is error in production `src` but off here.
      "@typescript-eslint/no-non-null-assertion": "off",
      // AE-0202: `no-img-element` targets production LCP/bandwidth. Tests
      // legitimately MOCK `next/image` with a plain `<img>` (so component tests
      // don't pull Next's Image runtime); the rule is `error` in production `src`
      // but off in test files for that idiomatic mock pattern.
      "@next/next/no-img-element": "off",
    },
  },
]);
