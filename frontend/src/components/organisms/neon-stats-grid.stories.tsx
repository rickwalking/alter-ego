import type { Meta, StoryObj } from "@storybook/react";
import { NeonStatsGrid } from "./neon-stats-grid";

const meta = {
  title: "Organisms/NeonStatsGrid",
  component: NeonStatsGrid,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonStatsGrid>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { cards: [{ label: "Posts", value: "12" }] },
};
