import type { Meta, StoryObj } from "@storybook/react";
import { NeonLink } from "./neon-link";

const meta = {
  title: "Atoms/NeonLink",
  component: NeonLink,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonLink>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { href: "/", children: "Neon Link" } };
