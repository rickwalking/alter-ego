import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import pluginQuery from "@tanstack/eslint-plugin-query";
import sonarjs from "eslint-plugin-sonarjs";

// AE-0166 — severity policy. `error` rules gate under `eslint --quiet`; `warn`
// rules are surfaced and enforced diff-scoped by `lint:changed`
// (`--max-warnings=0` on changed files), so NEW code cannot add them while the
// pre-existing backlog is paid down. Rules kept at `warn` are JUSTIFIED
// exceptions — promoting them to a global error would require mass refactoring of
// pre-existing violations (counts measured 2026-06-17):
//   no-unnecessary-condition (69), prefer-nullish-coalescing (50),
//   no-floating-promises (17), no-misused-promises (15), no-non-null-assertion
//   (7), no-img-element (8), and the size/complexity rules below. They shrink via
//   the diff-scoped gate, never blanket-ignored.
const typeCheckedRules = {
  "@typescript-eslint/no-explicit-any": "error",
  "@typescript-eslint/no-non-null-assertion": "warn",
  "@typescript-eslint/no-floating-promises": "warn",
  "@typescript-eslint/no-misused-promises": "warn",
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
      "max-params": ["warn", 3],
      "max-statements": ["warn", 25],
      "sonarjs/cognitive-complexity": ["warn", 15],
      "@tanstack/query/exhaustive-deps": "error",
      // AE-0166: 0 pre-existing violations -> error.
      "no-console": ["error", { allow: ["warn", "error"] }],
      "@next/next/no-img-element": "warn",
      // Data-fetching anti-patterns (AE-0166; frontend/CLAUDE.md "NEVER use
      // useEffect for Data Fetching"). fetch-in-useEffect ERRORS (0 pre-existing
      // violations); steer to TanStack Query / a Server Component / authenticated-fetch.
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
    // AE-0166: raw fetch() in client component/hook code is a data-fetching
    // anti-pattern (use TanStack Query / authenticated-fetch). `warn` because a
    // pre-existing backlog exists (admin dialogs, use-auth, etc.) — diff-scoped
    // `lint:changed` blocks NEW occurrences. API route handlers (app/api/**, the
    // backend proxies) and lib/** legitimately call fetch and are excluded.
    files: ["src/modules/**/*.{ts,tsx}", "src/components/**/*.{ts,tsx}"],
    ignores: ["**/*.test.*", "**/*.spec.*", "**/*.stories.*"],
    rules: {
      "no-restricted-syntax": [
        "warn",
        {
          selector: "CallExpression[callee.name='fetch']",
          message:
            "Avoid raw fetch() in components/hooks — use TanStack Query or authenticated-fetch (frontend/CLAUDE.md).",
        },
      ],
    },
  },
  {
    files: ["src/app/**/page.tsx"],
    rules: {
      // Warn globally; diff-scoped CI (lint:changed) enforces with --max-warnings=0.
      "max-lines": [
        "warn",
        { max: 200, skipBlankLines: true, skipComments: true },
      ],
      "max-lines-per-function": [
        "warn",
        { max: 40, skipBlankLines: true, skipComments: true, IIFEs: true },
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
    files: ["src/features/blog/components/public-post/**/*.tsx"],
    rules: {
      "@next/next/no-img-element": "off",
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
    },
  },
]);
