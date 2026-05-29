import type { Meta, StoryObj } from "@storybook/react";
import { NeonSkeleton } from "./neon-skeleton";

const meta = {
  title: "Atoms/NeonSkeleton",
  component: NeonSkeleton,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonSkeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { className: "h-8 w-32" } };
