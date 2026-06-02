import type { Meta, StoryObj } from "@storybook/react";
import { NeonAlert, NeonAlertTitle, NeonAlertDescription } from "./neon-alert";

const meta = {
  title: "Molecules/NeonAlert",
  component: NeonAlert,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonAlert>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <NeonAlert>
      <NeonAlertTitle>Notice</NeonAlertTitle>
      <NeonAlertDescription>Details here</NeonAlertDescription>
    </NeonAlert>
  ),
};
