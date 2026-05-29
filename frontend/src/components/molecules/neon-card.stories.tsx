import type { Meta, StoryObj } from "@storybook/react";
import { NeonCard } from "./neon-card";

const meta = {
  title: "Molecules/NeonCard",
  component: NeonCard,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { children: "Card content", title: "Card Title" } };
