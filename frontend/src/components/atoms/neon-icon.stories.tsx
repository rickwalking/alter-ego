import type { Meta, StoryObj } from "@storybook/react";
import { NeonIcon } from "./neon-icon";

const meta = {
  title: "Atoms/NeonIcon",
  component: NeonIcon,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonIcon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { path: "M12 5v14M5 12h14" } };
