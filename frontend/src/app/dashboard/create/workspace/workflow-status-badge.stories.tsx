import type { Meta, StoryObj } from "@storybook/react";
import { NextIntlClientProvider } from "next-intl";
import enMessages from "@/i18n/locales/en.json";
import { WorkflowStatusBadge } from "./workflow-status-badge";

const meta: Meta<typeof WorkflowStatusBadge> = {
  title: "Create/WorkflowStatusBadge",
  component: WorkflowStatusBadge,
  decorators: [
    (Story) => (
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <Story />
      </NextIntlClientProvider>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof WorkflowStatusBadge>;

const STATES = [
  "pending",
  "in_progress",
  "awaiting_human",
  "approved",
  "approved_for_publish",
  "published",
  "rejected",
  "failed",
  "brand_new_state",
] as const;

export const AllStates: Story = {
  render: () => (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
      {STATES.map((status) => (
        <WorkflowStatusBadge key={status} status={status} />
      ))}
    </div>
  ),
};

export const LabelOverride: Story = {
  name: "Phase name coloured by status",
  render: () => (
    <div style={{ display: "flex", gap: 12 }}>
      <WorkflowStatusBadge status="in_progress" label="content" />
      <WorkflowStatusBadge status="failed" label="images" />
    </div>
  ),
};
