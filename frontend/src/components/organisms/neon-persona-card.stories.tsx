import type { Meta, StoryObj } from "@storybook/react";
import { NeonPersonaCard } from "./neon-persona-card";

const meta = {
  title: "Organisms/NeonPersonaCard",
  component: NeonPersonaCard,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonPersonaCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    name: "Pedro",
    role: "Engineer",
    description: "RAG builder",
    skills: ["Python"],
  },
};
