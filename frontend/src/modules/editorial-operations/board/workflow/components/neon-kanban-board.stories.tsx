import type { Meta, StoryObj } from "@storybook/react";
import { NeonKanbanBoard } from "./neon-kanban-board";

const meta = {
  title: "Organisms/NeonKanbanBoard",
  component: NeonKanbanBoard,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonKanbanBoard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    columns: [
      {
        phase: "research",
        status: "Research",
        count: 1,
        cards: [
          {
            id: "1",
            title: "DeepSeek V4 Analysis",
            description: "Research open-source LLM benchmarks.",
            phase: "research",
            phaseStatus: "awaiting_human",
            statusKey: "awaiting_human",
            statusVariant: "magenta",
            assignee: "PM",
          },
        ],
      },
      {
        phase: "content",
        status: "Content",
        cards: [],
      },
    ],
    labels: {
      emptyColumn: "Nenhum projeto",
      expandColumn: (name: string, count: number) =>
        `Expandir coluna ${name} (${count})`,
      collapseColumn: (name: string) => `Recolher coluna ${name}`,
    },
  },
};
