import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

/**
 * Stryker-only vitest config. The production `vitest.config.ts` runs
 * babel-plugin-react-compiler, which conflicts with Stryker's mutation
 * instrumenter — both rewrite the AST and you end up with duplicated
 * `stryNS_9fa48` declarations that break the parser before any tests
 * run. Stripping the compiler plugin here keeps Stryker happy; the
 * real test runs still use the main config.
 */
export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"],
    exclude: [
      "**/node_modules/**",
      "**/dist/**",
      "**/cypress/**",
      "**/.{idea,git,cache,output,temp}/**",
    ],
    clearMocks: true,
    mockReset: true,
    restoreMocks: true,
    pool: "forks",
    testTimeout: 10000,
    hookTimeout: 10000,
  },
});
