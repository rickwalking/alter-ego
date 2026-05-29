import type { Meta, StoryObj } from "@storybook/react";
import { NeonRubricCard } from "./neon-rubric-card";

const meta = {
  title: "Organisms/NeonRubricCard",
  component: NeonRubricCard,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonRubricCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { title: "Voice", category: "Persona", score: 82, criteria: ["Tone"] } };
