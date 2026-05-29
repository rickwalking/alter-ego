import type { Meta, StoryObj } from "@storybook/react";
import { NeonSidebar } from "./neon-sidebar";

const meta = {
  title: "Organisms/NeonSidebar",
  component: NeonSidebar,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonSidebar>;

export default meta;
type Story = StoryObj<typeof meta>;

import { DASHBOARD_SIDEBAR_SECTIONS } from "./constants";
export const Default: Story = { args: { sections: DASHBOARD_SIDEBAR_SECTIONS } };
