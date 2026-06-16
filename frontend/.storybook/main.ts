import type { StorybookConfig } from "@storybook/nextjs-vite";
import path from "node:path";

const config: StorybookConfig = {
  stories: [
    "../src/components/atoms/**/*.stories.@(ts|tsx)",
    "../src/components/molecules/**/*.stories.@(ts|tsx)",
    "../src/components/organisms/**/*.stories.@(ts|tsx)",
    // AE-0140: business components re-homed into bounded-context modules keep
    // their co-located stories — discover them in their new module homes.
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
        "@": path.resolve(__dirname, "../src"),
      };
    }
    return config;
  },
};

export default config;
