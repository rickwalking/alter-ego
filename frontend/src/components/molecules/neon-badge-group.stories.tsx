import type { Meta, StoryObj } from "@storybook/react";
import { NeonBadgeGroup } from "./neon-badge-group";

const meta = {
  title: "Molecules/NeonBadgeGroup",
  component: NeonBadgeGroup,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonBadgeGroup>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { items: [{ label: "Active", variant: "cyan" }] },
};
