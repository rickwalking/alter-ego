import type { KnipConfig } from "knip";

/**
 * Knip configuration: dead files, exports, types and dependencies.
 *
 * `compilers.css` turns CSS `@import`s into imports so the Tailwind v4 entry
 * (`@import "tailwindcss"` in `globals.css`) counts as a use of `tailwindcss`.
 *
 * `husky.config` points at the repo-root hooks (core.hooksPath), which run
 * `lint-staged` and `commitlint` from this package.
 *
 * `ignoreDependencies` reason (the only entry): `braces` is the local patched
 * package (`file:scripts/braces-patched`) that the `"$braces"` override in
 * package.json references; npm requires it as a direct dependency, and no
 * source file imports it.
 */
const config: KnipConfig = {
  entry: [
    "src/app/**/{page,layout,template,loading,error,not-found,global-error,route,default}.{ts,tsx}",
    "src/app/**/{sitemap,robots,manifest,icon,apple-icon,opengraph-image,twitter-image}.{ts,tsx}",
    "src/middleware.{ts,tsx}",
    "next.config.{js,mjs,ts}",
    "src/**/*.stories.{ts,tsx}",
    "src/**/*.{test,spec}.{ts,tsx}",
    "*.config.{ts,mts,js,mjs,cjs}",
    "scripts/**/*.mjs",
    "src/components/{atoms,molecules}/index.ts",
    "src/modules/**/index.ts",
    "src/app/**/index.ts",
  ],
  project: ["src/**/*.{ts,tsx,css}"],
  ignoreExportsUsedInFile: true,
  next: true,
  vitest: true,
  storybook: true,
  husky: {
    config: ["../.husky/pre-commit", "../.husky/commit-msg"],
  },
  compilers: {
    css: (text: string): string =>
      [...text.matchAll(/(?<=@)import[^;]+/g)].join("\n"),
  },
  ignoreDependencies: ["braces"],
};

export default config;
