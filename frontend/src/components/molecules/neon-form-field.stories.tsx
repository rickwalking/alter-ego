import type { Meta, StoryObj } from "@storybook/react";
import { NeonFormField } from "./neon-form-field";

const meta = {
  title: "Molecules/NeonFormField",
  component: NeonFormField,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonFormField>;

export default meta;
type Story = StoryObj<typeof meta>;

import { NeonInput } from "@/components/atoms/neon-input";
export const Default: Story = {
  render: () => (
    <NeonFormField name="email" label="Email" required={false}>
      <NeonInput />
    </NeonFormField>
  ),
};
