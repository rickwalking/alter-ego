import type { Meta, StoryObj } from "@storybook/react";
import { NeonBadge } from "./neon-badge";

const meta = {
  title: "Atoms/NeonBadge",
  component: NeonBadge,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonBadge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { children: "Active", variant: "cyan" } };
