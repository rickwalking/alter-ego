import type { Meta, StoryObj } from "@storybook/react";
import { NeonSelect } from "./neon-select";

const meta = {
  title: "Atoms/NeonSelect",
  component: NeonSelect,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonSelect>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <NeonSelect>
      <option>One</option>
    </NeonSelect>
  ),
};
