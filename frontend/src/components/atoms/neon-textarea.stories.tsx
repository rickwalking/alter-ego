import type { Meta, StoryObj } from "@storybook/react";
import { NeonTextarea } from "./neon-textarea";

const meta = {
  title: "Atoms/NeonTextarea",
  component: NeonTextarea,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonTextarea>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { placeholder: "Write here..." } };
