import type { Meta, StoryObj } from "@storybook/react";
import { NeonPagination } from "./neon-pagination";

const meta = {
  title: "Organisms/NeonPagination",
  component: NeonPagination,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonPagination>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { total: 100, page: 1 } };
