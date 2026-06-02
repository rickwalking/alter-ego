import type { Meta, StoryObj } from "@storybook/react";
import { NeonToast } from "./neon-toast";

const meta = {
  title: "Molecules/NeonToast",
  component: NeonToast,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonToast>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { message: "Saved successfully" } };
