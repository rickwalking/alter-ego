import type { Meta, StoryObj } from "@storybook/react";
import { NeonBreadcrumb } from "./neon-breadcrumb";

const meta = {
  title: "Organisms/NeonBreadcrumb",
  component: NeonBreadcrumb,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonBreadcrumb>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { items: [{ label: "Home", href: "/" }, { label: "Dashboard" }] },
};
