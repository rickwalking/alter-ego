import type { Meta, StoryObj } from '@storybook/react';
import { Input } from './input';

const meta = {
  title: 'UI/Input',
  component: Input,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    placeholder: 'Enter text...',
  },
};

export const Email: Story = {
  args: {
    type: 'email',
    placeholder: 'Email address',
  },
};

export const Password: Story = {
  args: {
    type: 'password',
    placeholder: 'Password',
  },
};

export const Disabled: Story = {
  args: {
    placeholder: 'Disabled input',
    disabled: true,
  },
};

export const WithValue: Story = {
  args: {
    value: 'Hello World',
  },
};

export const GlassMorphic: Story = {
  args: {
    placeholder: 'Glass input...',
    className: 'glass-input w-[300px]',
  },
};

export const ChatInput: Story = {
  render: () => (
    <div className="w-[400px] flex gap-2">
      <Input
        placeholder="Type your message..."
        className="glass-input flex-1"
      />
      <button className="glass-button-primary px-4 py-2 rounded-lg text-white">
        Send
      </button>
    </div>
  ),
};
