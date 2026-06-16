import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import pluginQuery from "@tanstack/eslint-plugin-query";
import sonarjs from "eslint-plugin-sonarjs";

const typeCheckedRules = {
  "@typescript-eslint/no-explicit-any": "error",
  "@typescript-eslint/no-non-null-assertion": "warn",
  "@typescript-eslint/no-floating-promises": "warn",
  "@typescript-eslint/no-misused-promises": "warn",
  "@typescript-eslint/prefer-nullish-coalescing": "warn",
  "@typescript-eslint/prefer-optional-chain": "warn",
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
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "@next/next/no-img-element": "warn",
      "no-restricted-syntax": [
        "warn",
        {
          selector:
            "CallExpression[callee.name='useEffect'] CallExpression[callee.name='fetch']",
          message:
            "Avoid fetch() inside useEffect — prefer TanStack Query or a Server Component.",
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
    files: ["**/*.test.ts", "**/*.test.tsx", "tests/**"],
    rules: {
      "max-lines-per-function": "off",
      "max-lines": "off",
      complexity: "off",
      "max-statements": "off",
      "sonarjs/cognitive-complexity": "off",
    },
  },
]);
