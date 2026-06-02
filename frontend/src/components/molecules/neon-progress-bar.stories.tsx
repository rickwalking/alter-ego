import type { Meta, StoryObj } from "@storybook/react";
import { NeonProgressBar } from "./neon-progress-bar";

const meta = {
  title: "Molecules/NeonProgressBar",
  component: NeonProgressBar,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonProgressBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { value: 2, max: 5, label: "Progress" } };
