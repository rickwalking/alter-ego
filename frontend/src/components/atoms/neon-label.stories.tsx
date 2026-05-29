import type { Meta, StoryObj } from "@storybook/react";
import { NeonLabel } from "./neon-label";

const meta = {
  title: "Atoms/NeonLabel",
  component: NeonLabel,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonLabel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { children: "Email" } };
