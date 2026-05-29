import type { Meta, StoryObj } from "@storybook/react";
import { NeonSearchBar } from "./neon-search-bar";

const meta = {
  title: "Molecules/NeonSearchBar",
  component: NeonSearchBar,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonSearchBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { placeholder: "Search...", value: "", onChange: () => undefined } };
