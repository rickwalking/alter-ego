import type { Meta, StoryObj } from "@storybook/react";
import { NeonActivityList } from "./neon-activity-list";

const meta = {
  title: "Organisms/NeonActivityList",
  component: NeonActivityList,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonActivityList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    title: "Recent",
    activities: [
      { id: "1", title: "Published", time: "2h ago", badge: "live" },
    ],
  },
};
