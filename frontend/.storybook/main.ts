import type { StorybookConfig } from "@storybook/nextjs-vite";
import path from "node:path";

const config: StorybookConfig = {
  stories: [
    "../src/components/atoms/**/*.stories.@(ts|tsx)",
    "../src/components/molecules/**/*.stories.@(ts|tsx)",
    "../src/components/organisms/**/*.stories.@(ts|tsx)",
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
        "@": path.resolve(__dirname, "../src"),
      };
    }
    return config;
  },
};

export default config;
