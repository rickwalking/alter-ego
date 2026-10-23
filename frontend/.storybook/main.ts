import type { StorybookConfig } from "@storybook/nextjs-vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const STORYBOOK_DIR = path.dirname(fileURLToPath(import.meta.url));

const config: StorybookConfig = {
  stories: [
    "../src/components/atoms/**/*.stories.@(ts|tsx)",
    "../src/components/molecules/**/*.stories.@(ts|tsx)",
    "../src/components/organisms/**/*.stories.@(ts|tsx)",
    "../src/modules/**/*.stories.@(ts|tsx)",
  ],
  addons: ["@storybook/addon-a11y"],
  framework: {
    name: "@storybook/nextjs-vite",
    options: {},
  },
  staticDirs: ["../public"],
  viteFinal: async (config) => {
    if (config.resolve) {
      config.resolve.alias = {
        ...config.resolve.alias,
        "@": path.resolve(STORYBOOK_DIR, "../src"),
      };
    }
    return config;
  },
};

export default config;
