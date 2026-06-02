import type { Meta, StoryObj } from "@storybook/react";
import { NeonScanlineOverlay } from "./neon-scanline-overlay";

const meta = {
  title: "Organisms/NeonScanlineOverlay",
  component: NeonScanlineOverlay,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonScanlineOverlay>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <div style={{ height: 200 }}>
      <NeonScanlineOverlay />
    </div>
  ),
};
