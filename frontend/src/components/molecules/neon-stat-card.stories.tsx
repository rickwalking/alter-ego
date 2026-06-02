import type { Meta, StoryObj } from "@storybook/react";
import { NeonStatCard } from "./neon-stat-card";

const meta = {
  title: "Molecules/NeonStatCard",
  component: NeonStatCard,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonStatCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { label: "Views", value: "1.2k" } };
