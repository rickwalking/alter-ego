import type { Meta, StoryObj } from "@storybook/react";
import {
  NeonTabs,
  NeonTabList,
  NeonTabTrigger,
  NeonTabPanel,
} from "./neon-tab";

const meta = {
  title: "Molecules/NeonTabs",
  component: NeonTabs,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonTabs>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <NeonTabs defaultValue="tab1">
      <NeonTabList>
        <NeonTabTrigger value="tab1">Tab 1</NeonTabTrigger>
        <NeonTabTrigger value="tab2">Tab 2</NeonTabTrigger>
      </NeonTabList>
      <NeonTabPanel value="tab1">Panel 1</NeonTabPanel>
      <NeonTabPanel value="tab2">Panel 2</NeonTabPanel>
    </NeonTabs>
  ),
};
