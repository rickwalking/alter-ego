import type { Meta, StoryObj } from "@storybook/react";
import { NeonDropdown } from "./neon-dropdown";

const meta = {
  title: "Molecules/NeonDropdown",
  component: NeonDropdown,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonDropdown>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { render: () => <NeonDropdown><span>Menu</span></NeonDropdown> };
