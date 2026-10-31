import type { Meta, StoryObj } from "@storybook/react";
import { NextIntlClientProvider } from "next-intl";
import en from "@/i18n/locales/en.json";
import { NeonPersonaCard } from "./neon-persona-card";

const meta = {
  title: "Organisms/NeonPersonaCard",
  component: NeonPersonaCard,
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <NextIntlClientProvider locale="en" messages={en} timeZone="UTC">
        <Story />
      </NextIntlClientProvider>
    ),
  ],
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

export const NoLetterName: Story = {
  args: {
    name: "123 ⚙",
    role: "Persona",
    description: "No description",
    skills: ["A1", "A2", "A3", "A4", "A5", "A6"],
    hiddenSkills: ["A7", "A8"],
  },
};
