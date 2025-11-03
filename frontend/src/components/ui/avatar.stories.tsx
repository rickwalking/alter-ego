import type { Meta, StoryObj } from '@storybook/react';
import { Avatar, AvatarImage, AvatarFallback } from './avatar';

const meta = {
  title: 'UI/Avatar',
  component: Avatar,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof Avatar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Avatar>
      <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
      <AvatarFallback>CN</AvatarFallback>
    </Avatar>
  ),
};

export const WithFallback: Story = {
  render: () => (
    <Avatar>
      <AvatarImage src="https://invalid-url.example.com/image.jpg" alt="User" />
      <AvatarFallback>JD</AvatarFallback>
    </Avatar>
  ),
};

export const UserMessage: Story = {
  render: () => (
    <div className="flex items-center gap-3">
      <Avatar className="border-2 border-primary-600">
        <AvatarFallback className="bg-primary-600/20 text-primary-400">U</AvatarFallback>
      </Avatar>
      <div className="text-text-primary">User message</div>
    </div>
  ),
};

export const AIMessage: Story = {
  render: () => (
    <div className="flex items-center gap-3">
      <Avatar className="border-2 border-primary-400 animate-glow-pulse">
        <AvatarFallback className="bg-primary-600/40 text-primary-200">AI</AvatarFallback>
      </Avatar>
      <div className="text-text-primary">AI response</div>
    </div>
  ),
};

export const ChatConversation: Story = {
  render: () => (
    <div className="w-[400px] space-y-4">
      <div className="flex items-start gap-3">
        <Avatar className="border-2 border-primary-600">
          <AvatarFallback className="bg-primary-600/20 text-primary-400">U</AvatarFallback>
        </Avatar>
        <div className="flex-1 glass-card p-3 rounded-lg">
          <p className="text-sm text-text-primary">What's your background?</p>
        </div>
      </div>

      <div className="flex items-start gap-3">
        <Avatar className="border-2 border-primary-400">
          <AvatarFallback className="bg-primary-600/40 text-primary-200">AI</AvatarFallback>
        </Avatar>
        <div className="flex-1 glass-card p-3 rounded-lg">
          <p className="text-sm text-text-primary">
            I'm a senior software engineer with 10+ years of experience...
          </p>
        </div>
      </div>
    </div>
  ),
};

export const Sizes: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <Avatar className="h-8 w-8">
        <AvatarFallback className="text-xs">SM</AvatarFallback>
      </Avatar>
      <Avatar>
        <AvatarFallback>MD</AvatarFallback>
      </Avatar>
      <Avatar className="h-16 w-16">
        <AvatarFallback className="text-lg">LG</AvatarFallback>
      </Avatar>
    </div>
  ),
};
