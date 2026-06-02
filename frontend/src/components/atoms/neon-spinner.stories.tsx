import type { Meta, StoryObj } from "@storybook/react";
import { NeonSpinner } from "./neon-spinner";

const meta = {
  title: "Atoms/NeonSpinner",
  component: NeonSpinner,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonSpinner>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { size: "md" } };
