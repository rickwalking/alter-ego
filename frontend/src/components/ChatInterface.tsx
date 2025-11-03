import { useState, useEffect, useRef } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { sendMessage, ApiError } from '@/services/api';
import type { Message } from '@/types';

/**
 * Chat Interface Component
 *
 * Features:
 * - Real-time message display with ScrollArea
 * - User/AI message distinction with Avatar
 * - Auto-scroll to latest message
 * - Loading state during API calls
 * - Error handling for backend unavailability
 * - Liquid glass morphism styling
 */
export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async () => {
    // Validate input
    if (!inputMessage.trim()) {
      return;
    }

    // Clear error state
    setError(null);

    // Create user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      content: inputMessage,
      role: 'user',
      timestamp: new Date().toISOString(),
    };

    // Add user message to chat
    setMessages((prev) => [...prev, userMessage]);

    // Clear input
    setInputMessage('');

    // Set loading state
    setIsLoading(true);

    try {
      // Send message to backend
      const response = await sendMessage(inputMessage);

      // Create AI response message
      const aiMessage: Message = {
        id: crypto.randomUUID(),
        content: response.response,
        role: 'assistant',
        timestamp: response.timestamp,
      };

      // Add AI response to chat
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      // Handle error
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-4 h-[600px] flex flex-col">
      {/* Chat Messages */}
      <ScrollArea
        className="flex-1 glass-card glass-scroll p-4 mb-4 rounded-xl"
        ref={scrollRef}
      >
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-text-tertiary text-sm">
            Start a conversation by typing a message below
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex items-start gap-3 animate-[message-in_0.3s_ease-out]`}
              >
                {/* Avatar */}
                <Avatar className={`border-2 ${
                  message.role === 'user'
                    ? 'border-primary-600'
                    : 'border-primary-400'
                }`}>
                  <AvatarFallback className={
                    message.role === 'user'
                      ? 'bg-primary-600/20 text-primary-400'
                      : 'bg-primary-600/40 text-primary-200'
                  }>
                    {message.role === 'user' ? 'U' : 'AI'}
                  </AvatarFallback>
                </Avatar>

                {/* Message Content */}
                <div className={`flex-1 glass-card p-3 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-primary-600/10'
                    : 'bg-white/5'
                }`}>
                  <p className="text-sm text-text-primary whitespace-pre-wrap">
                    {message.content}
                  </p>
                  <p className="text-xs text-text-tertiary mt-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3 mt-4 animate-[message-in_0.3s_ease-out]">
            <Avatar className="border-2 border-primary-400">
              <AvatarFallback className="bg-primary-600/40 text-primary-200 animate-pulse">
                AI
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 glass-card p-3 rounded-lg bg-white/5">
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-error/20 border border-error/50 text-error text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Input Area */}
      <div className="flex gap-2">
        <Input
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={isLoading}
          className="glass-input flex-1"
        />
        <Button
          onClick={handleSendMessage}
          disabled={isLoading || !inputMessage.trim()}
          className="glass-button-primary text-white"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </Button>
      </div>
    </div>
  );
}
