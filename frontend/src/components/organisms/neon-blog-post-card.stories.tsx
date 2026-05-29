import type { Meta, StoryObj } from "@storybook/react";
import { NeonBlogPostCard } from "./neon-blog-post-card";

const meta = {
  title: "Organisms/NeonBlogPostCard",
  component: NeonBlogPostCard,
  tags: ["autodocs"],
} satisfies Meta<typeof NeonBlogPostCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { id: "1", href: "/blog/1", title: "Post", createdAt: "2026-05-29" } };
