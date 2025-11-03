import type { Meta, StoryObj } from '@storybook/react';
import { ScrollArea } from './scroll-area';

const meta = {
  title: 'UI/ScrollArea',
  component: ScrollArea,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof ScrollArea>;

export default meta;
type Story = StoryObj<typeof meta>;

const sampleMessages = Array.from({ length: 20 }, (_, i) => ({
  id: i,
  content: `Message ${i + 1}: Lorem ipsum dolor sit amet, consectetur adipiscing elit.`,
}));

export const Default: Story = {
  render: () => (
    <ScrollArea className="h-[300px] w-[350px] rounded-md border p-4">
      {sampleMessages.map((msg) => (
        <div key={msg.id} className="mb-2">
          {msg.content}
        </div>
      ))}
    </ScrollArea>
  ),
};

export const ChatMessages: Story = {
  render: () => (
    <ScrollArea className="h-[400px] w-[400px] glass-card glass-scroll p-4">
      {sampleMessages.map((msg) => (
        <div key={msg.id} className="mb-4">
          <div className={`p-3 rounded-lg ${msg.id % 2 === 0 ? 'bg-primary-600/20' : 'bg-white/5'}`}>
            <p className="text-sm text-text-primary">{msg.content}</p>
          </div>
        </div>
      ))}
    </ScrollArea>
  ),
};

export const WithGlassScroll: Story = {
  render: () => (
    <ScrollArea className="h-[350px] w-[300px] glass-scroll rounded-xl p-4">
      <div className="space-y-2">
        {sampleMessages.map((msg) => (
          <div key={msg.id} className="text-sm text-text-secondary">
            {msg.content}
          </div>
        ))}
      </div>
    </ScrollArea>
  ),
};
