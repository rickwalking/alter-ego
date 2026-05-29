import type { Meta, StoryObj } from "@storybook/react";
import { NeonGridBackground } from "./neon-grid-background";

const meta = {
  title: "Organisms/NeonGridBackground",
  component: NeonGridBackground,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonGridBackground>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { render: () => <div style={{ height: 200 }}><NeonGridBackground /></div> };
