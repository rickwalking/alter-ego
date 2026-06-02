import type { Meta, StoryObj } from "@storybook/react";
import { NeonTopBar } from "./neon-top-bar";

const meta = {
  title: "Organisms/NeonTopBar",
  component: NeonTopBar,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonTopBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { title: "Dashboard", breadcrumb: [{ label: "home" }] },
};
