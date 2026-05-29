import type { Meta, StoryObj } from "@storybook/react";
import { NeonModal } from "./neon-modal";

const meta = {
  title: "Molecules/NeonModal",
  component: NeonModal,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonModal>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { open: true, onClose: () => undefined, children: "Modal body" } };
