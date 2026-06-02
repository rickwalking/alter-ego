import type { Meta, StoryObj } from "@storybook/react";
import { NeonInput } from "./neon-input";

const meta = {
  title: "Atoms/NeonInput",
  component: NeonInput,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonInput>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { placeholder: "Search..." } };
